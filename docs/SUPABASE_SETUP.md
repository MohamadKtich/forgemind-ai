# Supabase PostgreSQL Setup

ForgeMind AI keeps all database access behind FastAPI:

```text
Next.js → FastAPI → SQLAlchemy → Supabase PostgreSQL
```

The browser never receives the database password.

## 1. Create the project

Create a Supabase project, choose the closest region, save the database password, and disable automatic public exposure of new tables. RLS may remain enabled for Data API access; the backend uses a trusted PostgreSQL connection.

## 2. Copy a Session Pooler URL

From **Connect**, copy the shared **Session Pooler** connection string on port `5432`. Replace the password placeholder and URL-encode special characters.

Convert the prefix for SQLAlchemy and psycopg:

```env
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Never put this value in `frontend/.env.local`, a `NEXT_PUBLIC_` variable, screenshots, or GitHub.

## 3. Configure the backend

```bash
cd backend
cp .env.example .env
```

Set `DATABASE_URL` in `backend/.env`, generate a strong `SECRET_KEY`, replace the device and recovery keys, and set `SEED_DEFAULT_USERS=false` after the first controlled initialization.

## 4. Initialize tables

The application creates missing SQLAlchemy tables at startup. You may also run the reviewed SQL in `supabase/schema.sql` from Supabase SQL Editor.

```bash
python -m fastapi dev app/main.py --host 127.0.0.1 --port 8000
```

Open **Table Editor** and verify the application tables.

## 5. Migrate existing local data

Back up `backend/forgemind.db`, then run:

```bash
python scripts/migrate_database.py   --source sqlite:///./backend/forgemind.db   --target "$DATABASE_URL"
```

Run this once against an empty target database. Verify row counts before changing the application configuration.

## 6. Production checklist

- Store the connection string in the deployment platform's secret manager.
- Restrict CORS to deployed frontend origins.
- Disable local registration if accounts are managed centrally.
- Change all initial passwords.
- Configure backups and monitoring.
- Add Supabase Storage before deploying uploaded inspection images and generated reports.
- Add Supabase Auth and tenant-aware RLS before allowing direct browser access to Data API tables.
