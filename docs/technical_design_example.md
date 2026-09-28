# Technical Design (Example — POC Demo Only)

**Related User Story:** US-1042

## Approach
- New endpoint `POST /auth/reset-password/request` generates a signed, single-use
  token (JWT or DB-backed) with a 30-minute TTL and emails a reset link.
- New endpoint `POST /auth/reset-password/confirm` validates the token, checks
  expiry + single-use flag, and updates the password hash.
- Token is invalidated (marked used) immediately after a successful reset.
- Passwords are never written to logs; only user ID + timestamp are logged.
- A confirmation email is sent via the existing notification service after reset.

## Out of Scope
- Rate limiting on the request endpoint (tracked separately in TECH-DBT-88).
- SMS-based reset (future phase).

> Replace this file (or the PR-description section) with the real Technical
> Design for whatever ticket the PR is implementing.
