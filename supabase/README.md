# Supabase resources

- `schema.sql` is generated from the SQLAlchemy models for PostgreSQL review or initialization.
- The preferred application path is FastAPI → SQLAlchemy → Supabase PostgreSQL.
- Keep the Session Pooler connection string in `backend/.env` locally or in the deployment secret manager.
- Do not place database credentials in frontend variables.

See `docs/SUPABASE_SETUP.md` for the complete workflow.
