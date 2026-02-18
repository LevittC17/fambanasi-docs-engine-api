# Full API Surface

Summary: A concise reference of the API endpoints (37 total), their authentication requirements, and role/notes.

| Method | Path | Requires Auth | Role / Notes |
|---|---|---:|---|
| GET | /health | No | Public |
| POST | /api/v1/auth/login | No | Public |
| GET | /api/v1/auth/me | Yes | Any authenticated user |
| POST | /api/v1/auth/logout | Yes | Any authenticated user |
| GET | /api/v1/documents/{path} | No | Public |
| GET | /api/v1/documents/ | No | Public |
| POST | /api/v1/documents/ | Yes | Editor |
| PUT | /api/v1/documents/{path} | Yes | Editor |
| DELETE | /api/v1/documents/{path} | Yes | Editor |
| POST | /api/v1/drafts/ | Yes | Any authenticated user |
| GET | /api/v1/drafts/ | Yes | Any authenticated user |
| GET | /api/v1/drafts/{id} | Yes | Any authenticated user |
| PUT | /api/v1/drafts/{id} | Yes | Any authenticated user |
| DELETE | /api/v1/drafts/{id} | Yes | Any authenticated user |
| POST | /api/v1/drafts/{id}/submit | Yes | Any authenticated user |
| POST | /api/v1/drafts/{id}/review | Yes | Editor |
| POST | /api/v1/drafts/{id}/publish | Yes | Editor |
| GET | /api/v1/metadata/ | Yes | Any authenticated user |
| GET | /api/v1/metadata/stats | Yes | Any authenticated user |
| GET | /api/v1/metadata/{id} | Yes | Any authenticated user |
| POST | /api/v1/metadata/ | Yes | Editor |
| PUT | /api/v1/metadata/{id} | Yes | Editor |
| DELETE | /api/v1/metadata/{id} | Yes | Admin |
| PUT | /api/v1/metadata/bulk | Yes | Editor |
| GET | /api/v1/navigation/tree | No | Public |
| GET | /api/v1/navigation/breadcrumbs | No | Public |
| GET | /api/v1/search/ | No | Public |
| GET | /api/v1/search/suggestions | No | Public |
| GET | /api/v1/search/filters | No | Public |
| POST | /api/v1/media/upload | Yes | Editor |
| GET | /api/v1/media/ | Yes | Editor |
| DELETE | /api/v1/media/{path} | Yes | Editor |
| GET | /api/v1/users/ | Yes | Admin |
| GET | /api/v1/users/{id} | Yes | Admin |
| PUT | /api/v1/users/{id} | Yes | Admin |
| GET | /api/v1/users/{id}/activity | Yes | Admin |
| POST | /api/v1/webhooks/github | No (HMAC) | HMAC-verified webhook |

## Key Design Decisions

- **Docs-as-Code:** Every CMS save creates a real Git commit — no shadow storage
- **Supabase for Auth & Storage:** JWT tokens validated at dependency level, files stored in managed buckets
- **Metadata Cache:** PostgreSQL cache prevents GitHub API rate limit exhaustion for search
- **Audit Trail:** Every write operation (document, draft, media, role change) logged with actor, timestamp, and before/after state
- **Review Workflow:** Draft → In Review → Approved → Published, with required comments on rejection
- **HMAC Webhook Verification:** Constant-time comparison prevents timing attacks
- **Non-root Docker:** Security-hardened container runs as UID 1001
- **Multi-stage Build:** Build tools excluded from production image to reduce attack surface
- **Redis Rate Limiting:** Token-bucket per user with in-memory fallback if Redis is unavailable
