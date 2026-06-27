# Seed Data Service TODOs

Status Legend

- ⬜ Not Started
- 🚧 In Progress
- ✅ Completed
- ⏸ Blocked

---

# Epic 1 — Project Setup

| Priority | Task | Status |
|----------|------|--------|
| 1 | Create Seed Data Service package | ⬜ |
| 2 | Create CLI entry point | ⬜ |
| 3 | Add configuration loader | ⬜ |
| 4 | Add logging | ⬜ |
| 5 | Create service orchestrator | ⬜ |
| 6 | Add Faker integration | ⬜ |
| 7 | Add deterministic random seed support | ⬜ |
| 8 | Add environment protection (prevent production execution) | ⬜ |

---

# Epic 2 — Core Infrastructure

| Priority | Task | Status |
|----------|------|--------|
| 1 | Base Seeder interface | ⬜ |
| 2 | Seeder registry | ⬜ |
| 3 | Dependency resolution between seeders | ⬜ |
| 4 | Transaction management | ⬜ |
| 5 | Batch insert helper | ⬜ |
| 6 | Progress reporting | ⬜ |
| 7 | Rollback support | ⬜ |

---

# Epic 3 — Tenant Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate tenants | ⬜ |
| 2 | Generate tenant settings | ⬜ |
| 3 | Generate tenant metadata | ⬜ |
| 4 | Validate tenant uniqueness | ⬜ |

---

# Epic 4 — Organization Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate organizations | ⬜ |
| 2 | Link organizations to tenants | ⬜ |
| 3 | Generate organization metadata | ⬜ |
| 4 | Validate hierarchy | ⬜ |

---

# Epic 5 — User Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate users | ⬜ |
| 2 | Generate emails | ⬜ |
| 3 | Generate usernames | ⬜ |
| 4 | Generate profile data | ⬜ |
| 5 | Generate departments | ⬜ |
| 6 | Generate locations | ⬜ |
| 7 | Generate MFA status | ⬜ |
| 8 | Assign organizations | ⬜ |

---

# Epic 6 — Role & Permission Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Seed system roles | ⬜ |
| 2 | Seed permissions | ⬜ |
| 3 | Create role-permission mappings | ⬜ |
| 4 | Validate permission inheritance | ⬜ |

---

# Epic 7 — Membership Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Assign users to organizations | ⬜ |
| 2 | Assign user roles | ⬜ |
| 3 | Generate memberships | ⬜ |
| 4 | Validate memberships | ⬜ |

---

# Epic 8 — Group Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate groups | ⬜ |
| 2 | Assign members | ⬜ |
| 3 | Assign managers | ⬜ |
| 4 | Validate memberships | ⬜ |

---

# Epic 9 — Resource Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate resources | ⬜ |
| 2 | Generate classifications | ⬜ |
| 3 | Assign owners | ⬜ |
| 4 | Generate metadata | ⬜ |
| 5 | Generate tags | ⬜ |

---

# Epic 10 — Policy Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Seed RBAC policies | ⬜ |
| 2 | Seed ABAC policies | ⬜ |
| 3 | Generate policy conditions | ⬜ |
| 4 | Validate policies | ⬜ |

---

# Epic 11 — API Client Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate API clients | ⬜ |
| 2 | Generate service accounts | ⬜ |
| 3 | Generate client secrets | ⬜ |
| 4 | Generate scopes | ⬜ |

---

# Epic 12 — Audit Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate login events | ⬜ |
| 2 | Generate CRUD events | ⬜ |
| 3 | Generate policy changes | ⬜ |
| 4 | Generate timestamps | ⬜ |

---

# Epic 13 — Security Event Seeder

| Priority | Task | Status |
|----------|------|--------|
| 1 | Generate failed logins | ⬜ |
| 2 | Generate MFA failures | ⬜ |
| 3 | Generate denied requests | ⬜ |
| 4 | Generate suspicious logins | ⬜ |

---

# Epic 14 — CLI Commands

| Priority | Task | Status |
|----------|------|--------|
| 1 | make seed | ⬜ |
| 2 | make reseed | ⬜ |
| 3 | make reset-db | ⬜ |
| 4 | Seed by tenant | ⬜ |
| 5 | Seed by entity | ⬜ |
| 6 | Seed by size | ⬜ |
| 7 | Dry-run mode | ⬜ |

---

# Epic 15 — Testing

| Priority | Task | Status |
|----------|------|--------|
| 1 | Unit tests | ⬜ |
| 2 | Integration tests | ⬜ |
| 3 | Deterministic seed tests | ⬜ |
| 4 | Performance tests | ⬜ |
| 5 | CLI tests | ⬜ |

---

# Epic 16 — Documentation

| Priority | Task | Status |
|----------|------|--------|
| 1 | Architecture documentation | ⬜ |
| 2 | Configuration guide | ⬜ |
| 3 | CLI documentation | ⬜ |
| 4 | Developer guide | ⬜ |
| 5 | Example configurations | ⬜ |

---

# Future Enhancements

| Priority | Task | Status |
|----------|------|--------|
| 1 | Parallel seeding | ⬜ |
| 2 | Incremental seeding | ⬜ |
| 3 | Plugin system for new services | ⬜ |
| 4 | YAML/JSON fixture import | ⬜ |
| 5 | Synthetic large-scale datasets (1M+ records) | ⬜ |
| 6 | Performance benchmarking mode | ⬜ |
| 7 | Data anonymization from production snapshots | ⬜ |