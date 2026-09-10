# Supabase Integration Plan (Database + Auth)

## Objective
Use Supabase as the platform for both database and authentication. Keep sensitive operations server-side, allow frontend authentication flows with Supabase client using publishable key, and ensure privileged table operations use only backend service credentials.

## Scope
- Use Supabase Postgres as the system database.
- Use Supabase Auth for user authentication and session handling.
- Allow frontend to use Supabase client for auth flows only.
- Keep admin-level and protected data operations behind backend service role usage.

## Environment Contract
Backend `.env` should include:
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`

### Profile roles
- Use a `profiles` table (`user_id`, `email`, `role`) as the source of truth for authorization roles.
- Default new profiles to `student`; admins are granted by updating `profiles.role = 'admin'`.

Notes:
- `SUPABASE_SECRET_KEY` is backend-only and must never be exposed to frontend bundles.
- Frontend uses `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` only.

## Architecture Direction

### 1) Database layer on Supabase
- Keep all existing tables in Supabase Postgres (`public` schema unless later split is needed).
- Continue managing schema via SQL migrations (`backend/schema.sql` + migration scripts).
- Keep backend business logic in FastAPI services.

### 2) Authentication with Supabase
- Replace custom app JWT issuance/verification with Supabase Auth tokens.
- Frontend login/register/logout should use Supabase Auth client flows.
- Backend should verify Supabase JWTs and derive user identity from claims.
- Map authenticated Supabase users to app-level student/admin behavior as needed.

### 3) Frontend integration (auth only)
- Add Supabase client setup in frontend for auth/session state.
- Keep data CRUD through backend API unless a specific read-only path is intentionally opened.
- Do not expose `SUPABASE_SECRET_KEY` in frontend env or code.

### 4) Backend service-role usage
- Use `SUPABASE_SECRET_KEY` only in backend for privileged operations:
  - admin imports/exports
  - protected table maintenance
  - server-side user management tasks when required
- Avoid sending service-role responses directly without backend validation/filtering.

### 5) Table access and security model
- Since frontend auth is now allowed, do not use blanket deny rules meant for backend-only mode.
- Enforce access using a combination of:
  - Row Level Security (RLS) policies for user-facing access paths
  - Backend service-role for privileged operations
- Keep policies explicit per table and operation (select/insert/update/delete).

## Implementation Steps
1. Sanitize `backend/.env.example` and align with the new env contract.
2. Add Supabase Auth integration in frontend (client + session lifecycle).
3. Update backend auth dependency to validate Supabase JWTs.
4. Add backend Supabase admin client utility using `SUPABASE_SECRET_KEY`.
5. Define/apply RLS policies for user-facing tables where direct auth access is needed.
6. Keep admin and sensitive operations routed through backend service-role endpoints.

## Verification Checklist
- Auth flow:
  - User can sign up/sign in/sign out via Supabase Auth in frontend.
  - Backend accepts and validates Supabase-issued JWTs.
- Security:
  - `SUPABASE_SECRET_KEY` is only present in backend runtime.
  - Frontend build contains only publishable key usage.
  - RLS policies prevent cross-user data access.
- Functional:
  - Quiz/session/admin flows still work end-to-end.
  - Import/export and privileged operations function through backend service-role paths.

## Deliverables
1. Updated plan and env contract documentation.
2. Frontend Supabase Auth integration notes.
3. Backend JWT verification update plan (Supabase tokens).
4. RLS policy plan per table.
5. Validation notes for auth + security + feature parity.

## Acceptance Criteria
- Supabase is used for both database and authentication.
- Frontend uses Supabase only with publishable key for auth/session.
- Backend uses `SUPABASE_SECRET_KEY` for privileged operations only.
- Sensitive table operations remain protected and policy-compliant.
