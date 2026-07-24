# ForgeMind AI API Guide

Interactive Swagger documentation is available at `http://localhost:8000/docs` while the backend is running.

## Authentication

Human routes use:

```http
Authorization: Bearer <access-token>
```

Identity routes:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `PATCH /api/auth/profile`
- `POST /api/auth/change-password`
- `POST /api/auth/recover-local`

## Operations

- `GET /api/dashboard`
- `GET|POST /api/factories`
- `PATCH|DELETE /api/factories/{factory_id}`
- `GET|POST /api/machines`
- `GET|PATCH|DELETE /api/machines/{machine_id}`
- `GET /api/predictive/latest`
- `GET /api/model/info`
- `GET /api/models/status`
- `GET|POST /api/production`

`GET /api/models/status` is the authoritative registry for installed model bundles, runtime mode, source data, held-out metrics, license, version, and limitations.

## Maintenance and alerts

- `GET /api/maintenance`
- `POST /api/machines/{machine_id}/maintenance`
- `PATCH /api/maintenance/{record_id}`
- `GET /api/alerts`
- `GET /api/alerts/summary`
- `PATCH /api/alerts/{alert_id}/read`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/acknowledge-all`

## Quality

- `POST /api/quality/inspect`
- `GET /api/quality/inspections`
- `GET /api/quality/stats`
- `GET /api/quality/images/{filename}`

The inspection request uses multipart form data and accepts a product image, an optional golden-reference image, product name, batch code, and machine ID.

## Assistant and reports

- `POST /api/assistant/query`
- `GET /api/assistant/conversations`
- `GET /api/assistant/conversations/{conversation_id}`
- `POST /api/reports/generate`
- `GET /api/reports`
- `GET /api/reports/{report_id}/download`
- `GET /api/reports/production.csv`

Assistant request:

```json
{
  "question": "لماذا الآلة M-002 معرضة للخطر؟",
  "locale": "ar"
}
```

Supported report types: `executive`, `maintenance`, `quality`, `production`, and `alerts`.

## Digital twin and devices

- `GET /api/simulation/status`
- `POST /api/simulation/configure`
- `POST /api/simulation/tick`
- `POST /api/simulation/{action}`
- `POST /api/hardware/readings`
- `POST|GET /api/device/commands`

Hardware ingestion uses:

```http
X-Device-Key: <configured-device-key>
```

## Administration

- `GET /api/admin/users`
- `PATCH /api/admin/users/{user_id}`
- `POST /api/admin/users/{user_id}/reset-password`
- `GET|PUT /api/admin/settings/{key}`
- `GET /api/admin/logs`

## Error format

```json
{
  "detail": "Human-readable error description"
}
```
