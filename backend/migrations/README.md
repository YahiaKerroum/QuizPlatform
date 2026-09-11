# Migrations

These are the incremental deltas that were applied, in order, against the
original Supabase project as the schema evolved. They're kept as a historical
record.

**A brand-new project doesn't need to run any of these.** `backend/schema.sql`
is the single, up-to-date, idempotent bootstrap — it already includes
everything below. Run that one file against a fresh database and you're done.
