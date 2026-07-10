# 0002. Merge UserManagement + UserLifecycleManagement + UserProfileManagement into User

Date: 2026-07-06
Status: Accepted

## Context

Same shape of problem as ADR 0001, one layer up: three separate services
(core identity CRUD, status lifecycle, profile/preferences/avatar/contact
metadata) talking to each other over HTTP, each needing a fake HTTP client
in the others' test suites to stand in for "the service across the wire."

## Decision

Merge into one service, `services/User/`. `UserStatus` becomes one enum
(`pending/active/suspended/locked/deactivated`) instead of two services'
separate state models; `UserStatusHistory` and the old `LifecycleEvent`
table become one audit table with an `action` column carrying the verb
distinction. Cross-service references that used to need FK-avoidance
(because they crossed a service boundary) became real
`ForeignKey(..., ondelete="CASCADE")` columns now that everything is one
database.

## Consequences

- One transaction covers a status transition and its audit row — no
  fire-and-log gap where the two could disagree.
- The `/api/v1/user-lifecycle` gateway prefix was removed outright (not
  renamed) — it only ever existed to keep two upstream containers from
  colliding at the gateway.
- Found two real bugs only real Docker/Postgres verification caught (a
  `CHECK` constraint never updated for `locked`, and non-time-ordered audit
  pagination under SQLite's second-resolution timestamps) — see
  `services/User/TODO.md` for both.
- A later audit (2026-07-06) found and fixed a cross-tenant IDOR in this
  merged service's profile/avatar/preferences/contacts endpoints — see ADR
  0006 and `services/User/TODO.md`.
