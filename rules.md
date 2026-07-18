# RULES.md — Working Rules for the Coding Agent

These rules govern how the agent (Cursor, Windsurf, Claude Code, etc.) should work on this repo. Read `prd.md`, `architecture.md`, and `phases.md` before writing code. When rules here conflict with a passing whim in chat, these rules win unless the human explicitly overrides them in writing.

## 1. Ground Rules

1. Don't touch anything outside the current phase's scope (see `phases.md`) unless it's a blocking bug in already-built code.
2. Every new Django app must be registered in `INSTALLED_APPS` and have `apps.py`, `models.py`, `admin.py`, `urls.py`, `services.py` (business logic), `serializers.py` (if it has API endpoints), and a `tests/` folder — even if some start nearly empty. Consistency beats minimalism here.
3. No feature is "done" until: migrations are created and applied cleanly, at least a minimal test exists, and it's reachable from the UI (not just the admin panel), unless the phase explicitly scopes it as backend-only.
4. If a decision in `prd.md` §10 (Open Questions) hasn't been resolved yet and blocks the current task, stop and ask rather than silently picking an assumption that contradicts the PRD.

## 2. Django Conventions

- Business logic lives in `services.py` per app, not in views or serializers. Views/viewsets orchestrate; they don't contain multi-step logic (e.g., booking a ride, transitioning trip status, processing a payment — all go through a service function).
- Model methods are fine for small, model-local logic (`ride.is_full()`); cross-model orchestration goes in `services.py`.
- Never write raw SQL unless a specific query is proven to need it (N+1 fixes should use `select_related`/`prefetch_related` first).
- All money fields use `DecimalField(max_digits=10, decimal_places=2)` — never `FloatField` for currency.
- All datetime fields are timezone-aware (`USE_TZ = True`); never call `datetime.now()` — use `django.utils.timezone.now()`.
- Every model that's organization-scoped inherits from a shared `OrgScopedModel`/uses `OrgScopedQuerySet` (see architecture.md §4) — don't hand-roll `.filter(organization=...)` inconsistently across apps.
- Use Django's built-in `User` extension via `AbstractUser` (custom `accounts.User`), set in `AUTH_USER_MODEL` **before the first migration is ever run** — this cannot be safely changed later. If migrations already exist without a custom user model, flag it immediately rather than proceeding.

## 3. API / DRF Conventions

- All API routes are versioned under `/api/` (no separate `/v1/` needed for hackathon scope, but keep the prefix so it's addable later).
- Use `ModelSerializer` where the API shape matches the model closely; use plain `Serializer` for actions that don't map 1:1 to a model (route-preview, payment-verify).
- Every viewset declares an explicit `permission_classes` — never rely on the DRF default alone for anything touching user or org data.
- Return DRF's standard error shape on validation failure (`{"field": ["message"]}`) — don't invent a custom error envelope.
- Pagination on any list endpoint that can realistically exceed ~50 rows (ride search results, ride history).

## 4. Real-Time / Async Rules

- Don't reach for Django Channels until the polling-based version of tracking/chat works end-to-end (see architecture.md ADR-2). If Channels is added, it lives in its own `consumers.py` per app and reuses the same permission checks as the REST equivalent — don't duplicate looser auth logic in the consumer.
- Anything that could take >1s of wall-clock time in a request (report aggregation, sending a notification/email) goes through Celery, not inline in the view.
- Location pings are write-heavy — don't add expensive synchronous work (e.g., recomputing full route geometry) on every single ping; throttle ETA recomputation (e.g., every 3rd ping or every 15s).

## 5. Payments Rules (hard rules, not guidelines)

- Every payment "success" must be verified server-side against Razorpay's response signature. A client-side "payment succeeded" callback alone is never sufficient to mark a `Payment` as `SUCCESS`.
- Wallet debits/credits are wrapped in a DB transaction with `select_for_update()` on the `Wallet` row — no read-then-write race conditions on balance.
- Never log full card numbers, CVV, or UPI PINs (Razorpay Checkout.js keeps these off our server anyway — don't build a form that collects them directly).
- Test-mode keys only, sourced from environment variables, never hardcoded or committed.

## 6. Concurrency / Data Integrity Rules

- Booking a ride (`Trip` creation against a `Ride`) must use `select_for_update()` on the `Ride` row and re-check `seats_available` inside the transaction before decrementing — this is the single most likely spot for a hackathon-demo-breaking race condition.
- Trip status transitions go only through the `transition()` function in `trips/services.py` (see architecture.md §5); illegal transitions raise, they don't silently no-op.

## 7. Security Rules

- Every view or viewset touching org-scoped data must filter by `request.user.organization` — treat a missing org filter as a bug, not a style nit.
- Role checks (`Admin` vs `Employee`) are enforced server-side on every relevant endpoint, not only hidden in the template/menu.
- CSRF stays enabled globally; don't disable it to "make AJAX easier."
- Secrets (`SECRET_KEY`, Razorpay keys, DB credentials, maps API key) live in `.env`, loaded via `django-environ` or equivalent — never committed, never hardcoded, `.env` is git-ignored.
- File uploads (profile photos, if implemented) validate content-type and size server-side, not just via the `accept` attribute on the input.

## 8. Testing Rules

- Every service function that mutates state (booking, status transition, payment verify, wallet debit) gets at least one happy-path test and one failure-path test (e.g., "booking when seats are full raises").
- Don't chase 100% coverage under hackathon time pressure — prioritize tests for money-handling and concurrency-sensitive code (§5, §6) over CRUD boilerplate.
- Use `pytest-django` or Django's own `TestCase`; pick one and stay consistent across the repo.

## 9. Git / Workflow Rules

- Branch per phase or per feature (`phase-2-vehicles`, `feat/live-tracking`), not one long-lived branch with everything.
- Commit messages describe the "what" in imperative mood (`Add ride booking service with seat-lock`), not `wip` or `fix stuff`.
- Migrations are committed alongside the model change that produced them, in the same commit — never leave uncommitted/uncreated migrations.
- Don't `git push --force` to a shared branch without explicit human sign-off.

## 10. UI/Template Rules

- Follow `design.md` for tokens (color, type, spacing) — don't invent new ad hoc colors/fonts per template.
- Server-rendered Django templates are the default; reach for JS only for: search-results refresh, map rendering, chat, live tracking, payment checkout modal. Don't rebuild static pages (settings, ride history, admin CRUD) as JS-heavy SPA-style pages when a plain form/template does the job faster and more reliably for a hackathon demo.
- Every form has both client-side (fast feedback) and server-side (source of truth) validation — never client-only.

## 11. What to Do When Blocked

- If a requirement in `prd.md` is ambiguous and the ambiguity changes the data model (not just copy/UI), stop and surface the specific question rather than guessing silently.
- If a phase in `phases.md` can't be completed in its allotted time, cut scope within that phase (drop a bonus sub-feature) rather than skipping ahead and leaving the mandatory feature half-built.
- Prefer the boring, well-understood Django pattern over a clever one — this is a time-boxed hackathon build that a judge will read/run, not a long-term production system (yet).

## 12. Definition of Done (per feature)

A feature is done when:
1. Migration exists and applies cleanly on a fresh DB.
2. It's reachable through the actual UI flow described in `prd.md`, not only via `/admin/` or a raw API call.
3. It respects organization scoping and role permissions.
4. It has at least minimal test coverage on its service-layer logic.
5. It's demoable in the end-to-end flow described in `prd.md` §11 without manual DB edits.
