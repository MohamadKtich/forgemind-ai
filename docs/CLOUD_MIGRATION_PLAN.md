# Cloud Migration Plan

The local release deliberately keeps cloud infrastructure separate from application completion. When the deployment phase begins, use the following sequence.

## 1. PostgreSQL schema

Translate the SQLAlchemy models in `backend/app/models.py` into Alembic migrations for PostgreSQL. Preserve foreign keys, indexes, timestamps, JSON fields, user roles, factory relationships, and audit history.

## 2. Managed authentication

Choose Supabase Auth, Auth0, Clerk, or another managed identity provider. Replace local token creation in the backend with verified provider JWTs while keeping the existing role dependencies and API contracts.

## 3. Object storage

Move inspection originals, references, annotated images, and generated reports from `backend/storage` to private object-storage buckets. Store object keys in the existing database fields and return signed download URLs.

## 4. Deployment

- Deploy the frontend to Vercel or a container platform.
- Deploy FastAPI to Railway, Render, Fly.io, Azure, AWS, or Google Cloud.
- Set production CORS origins.
- Use HTTPS and managed secrets.
- Add health monitoring, structured logs, alerts, and scheduled backups.

## 5. Industrial integration

Place a gateway inside the plant network. The gateway should translate MQTT, OPC-UA, Modbus, or vendor-specific protocols into the ForgeMind sensor and command contracts. Add per-device credentials, heartbeat status, retry handling, idempotency, and command acknowledgement.

## 6. Model validation

Retrain and validate the predictive and visual inspection models with labeled data from the target machines and products. Establish model-version approval, threshold governance, drift monitoring, and rollback procedures before automated decisions are used in operations.
