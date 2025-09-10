Step-by-Step Plan for Python (FastAPI) + Supabase (Postgres)
Phase 1 – Project Setup & Scaffolding

 Set up FastAPI project structure (routers, services, models).

 Configure Supabase/Postgres connection.

 Add Alembic for DB migrations.

 Configure environment management (dotenv / pydantic settings).

 Add JWT authentication boilerplate.

 Setup logging with correlation IDs (distributed tracing basics).

 Create a health-check endpoint.

Prompt (Phase 1)
"Generate a FastAPI project structure with JWT authentication, Supabase Postgres connection, Alembic migrations, and correlation ID logging. Include a health check endpoint and sample user table migration."

Phase 2 – Core Payment Flows

 Integrate with Authorize.Net Sandbox API using their Python SDK.

 Implement purchase flow (auth + capture in one step).

 Implement authorize + capture (two-step).

 Implement cancel (before capture).

 Implement refunds (full + partial).

 Persist transactions in DB with order_id, status, correlation_id.

 Expose endpoints for each flow with JWT protection.

Prompt (Phase 2)
"Using FastAPI and Authorize.Net Python SDK, implement endpoints for purchase, authorize+capture, cancel, and refund. Ensure JWT auth, transaction persistence in Postgres via Supabase, and correlation IDs in logs."

Phase 3 – Subscriptions / Recurring Billing

 Implement recurring billing setup with Authorize.Net.

 Store subscription metadata (plan, interval, status).

 Add endpoints to create, cancel, and query subscriptions.

 Sync subscription events with DB.

Prompt (Phase 3)
"Extend FastAPI service to support recurring billing with Authorize.Net. Implement subscription creation, cancelation, and retrieval endpoints. Persist subscription data in Postgres and include correlation IDs in logs."

Phase 4 – Webhooks & Event Handling

 Add webhook endpoint for async payment events.

 Verify webhook signatures.

 Store events in DB with idempotency handling (avoid duplicates).

 Use a queue (e.g., in-memory initially, then Celery/Redis if needed).

 Log all webhook events with correlation ID.

Prompt (Phase 4)
"Add webhook handling to FastAPI app for Authorize.Net events (payment success, refund, subscription updates). Verify signature, ensure idempotency, persist events in Postgres, and log with correlation IDs. Use a simple in-memory queue for retries."

Phase 5 – Reliability & Observability

 Implement idempotency key mechanism on client-initiated requests.

 Add metrics endpoint (Prometheus compatible).

 Add audit logs table.

 Enforce rate limiting (basic middleware).

 Expand test suite to ≥80% coverage.

Prompt (Phase 5)
"Enhance FastAPI app with idempotency key support, metrics endpoint (Prometheus style), audit logging table, and request rate limiting. Add unit tests with ≥80% coverage for all payment and webhook flows."

Phase 6 – Compliance & Documentation

 Document PCI DSS considerations (sensitive data never stored, use tokens).

 Document secrets management (Supabase, API keys in env).

 Write OpenAPI docs for all endpoints.

 Provide Postman collection or curl examples.

Prompt (Phase 6)
"Generate API documentation for all FastAPI endpoints (purchase, refund, subscription, webhook, etc.) including request/response examples. Add a section in docs covering PCI DSS handling, secrets management, rate limits, and audit logs."