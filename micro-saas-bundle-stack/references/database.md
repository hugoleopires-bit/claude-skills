# Database: Supabase as a generic key-value store

Portal CEMEC never designed a normalized relational schema for its domain
data (events, participants, checklists, suppliers, contracts...). Instead
it uses **one generic table** and treats Postgres/Supabase as a document
store, which is the right trade-off for a micro-SaaS: you want to ship
features fast and iterate on the data shape constantly, and a rigid schema
with migrations for every field addition is exactly the friction you're
trying to avoid by not having a build step either.

Use this pattern by default. Reach for real relational tables + foreign
keys only for things that actually need DB-level integrity (auth records,
anything with a uniqueness or referential constraint that matters — see
"When to break the pattern" below).

## The `blobs` table

```sql
create table if not exists blobs (
  chave  text primary key,
  valor  jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);
```

Each top-level slice of your app's client-side state becomes one row:
`chave = 'eventos'` holds a JSON array of all events, `chave = 'clientes'`
holds all clients, etc. On load, the frontend fetches every row it needs
and assembles them into `this.state`. On every mutation, it writes the
whole updated array back to its row (`update blobs set valor = $1 where
chave = $2`) — no per-field writes, no partial updates to reason about.

This is a **document store self-funded by Postgres**: you still get
`jsonb` querying, indexing (`create index on blobs using gin (valor)` if
you ever need to query inside a blob server-side), and transactions, but
without hand-designing a schema for every entity up front.

**Set this up** by calling `mcp__Supabase__create_project` (or using an
existing org's project), then `mcp__Supabase__apply_migration` with the
`create table` above as the first migration. Use `apply_migration` (not
`execute_sql`) for schema changes — it's versioned; save `execute_sql` for
one-off data fixes (see below) and ad-hoc reads.

## Auth: a real table, not the generic blob

Authentication is the one place Portal CEMEC does NOT use the blob
pattern — it uses a dedicated table with a real constraint, because login
credentials genuinely need uniqueness enforcement and because you don't
want every login attempt to deserialize a whole JSON array to find one
user.

```sql
create extension if not exists pgcrypto;

create table if not exists app_usuarios (
  id            bigint generated always as identity primary key,
  nome          text not null,
  usuario       text not null unique,
  senha_hash    text not null,
  email         text,
  cargo         text,
  perfil_acesso text not null default 'operador',
  secao         text,
  status        text not null default 'Ativo',
  created_at    timestamptz not null default now()
);

create or replace function hash_senha(p_senha text)
returns text
language sql
security definer
as $$
  select crypt(p_senha, gen_salt('bf'));
$$;

create or replace function verificar_senha(p_senha text, p_hash text)
returns boolean
language sql
security definer
as $$
  select p_hash = crypt(p_senha, p_hash);
$$;
```

The frontend never sees a plaintext-vs-hash comparison or a hashing
library — it calls `sb.rpc('hash_senha', { p_senha })` on signup/password
set, and `sb.rpc('verificar_senha', { p_senha, p_hash })` on login. This
gets you real bcrypt hashing with zero crypto code in the client bundle,
without adopting Supabase's full Auth product (which is heavier than a
small internal tool typically needs — email verification flows, magic
links, etc. you probably don't want). If your SaaS is public-facing or
needs OAuth/social login/password reset emails, use real Supabase Auth
instead; this lightweight RPC pattern is specifically for internal tools
with a known, small user base.

**Any other entity that genuinely needs a uniqueness or foreign-key
constraint** (not just auth) is a signal to give it a real table too —
the blob pattern trades away DB-level integrity for velocity, which is
the right trade for most of an app's data but not for all of it. Decide
per-entity, don't dogmatically blob everything.

## Data fixes: SQL, not migrations

Because there's no rigid schema for the blob data, a bad value that
crept into production (e.g. two near-duplicate category names from a
typo, like `"Pré evento"` vs `"Pré-evento"`) gets fixed with a one-off
`execute_sql` UPDATE against the live `blobs` row, not a versioned
migration file:

```sql
update blobs
set valor = (
  select jsonb_agg(
    case when item->>'fase' = 'Pré evento'
      then jsonb_set(item, '{fase}', '"Pré-evento"')
      else item end
  )
  from jsonb_array_elements(valor) item
)
where chave = 'checklist';
```

Always `select` to see the current distinct values first, confirm the
fix's shape on a `select` before running the `update`, and prefer exact
string matches over fuzzy patterns to avoid collateral changes. Pair this
with a code-level fix (validate/normalize at the point where the bad value
gets written) so the same bug doesn't reintroduce the same data rot —
fixing the data without fixing the write path just means you'll be back
here next month.
