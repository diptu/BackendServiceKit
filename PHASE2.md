# Phase 2 Plan: Performance Improvement
| Service ID & Name | Optimal Protocol | Rust Framework Stack | Expected Latency (p99) | Target Throughput Profile |
|---|---|---|---:|---|
| 1. Identity & Access Management (IAM) | gRPC / REST | tonic / axum | < 5ms (gRPC) / < 15ms (REST) | High (Read-Heavy) |
| 2. Authentication Service | gRPC / REST | tonic / axum | < 8ms (gRPC) / < 20ms (REST) | Medium |
| 3. Authorization Service | gRPC (In-Memory) | tonic (Decision Engine) | < 1ms | Extreme (100k+ req/sec) |
| 4. ABAC Policy Management | gRPC | tonic + sqlx | < 10ms | Low (Write) / High (Cached) |
| 5. ABAC Policy Evaluation Engine | gRPC (Local) | tonic + Custom Ast | < 1.5ms | Extreme |
| 6. RBAC Management Service | gRPC | tonic + sqlx | < 5ms | High (Cached via mini-moka) |
| 7. ReBAC Management Service | gRPC (Graph) | tonic + indradb | < 3ms | High |
| 8. User Management Service | gRPC / REST | tonic / axum | < 12ms | Medium |
| 9. User Profile Service | GraphQL | async-graphql + axum | < 15ms | High |
| 10. User Lifecycle Management | Event-Driven | rdkafka (Kafka) | Asynchronous (Sub-second) | High Burst |
| 11. Session Management Service | gRPC (Cached) | tonic + redis-rs | < 2ms | Extreme |
| 12. Device Management Service | REST | axum | < 15ms | Medium |
| 13. API Key Management Service | gRPC | tonic + mini-moka | < 1ms (Cache hit) | Extreme |
| 14. OAuth2/OpenID Connect | REST | axum + openidconnect | < 18ms | Medium |
| 15. Single Sign-On (SSO) Service | REST | axum | < 15ms | Medium |
| 16. SCIM Provisioning Service | REST | axum | < 25ms | Low |
| 17. Multi-Factor Auth (MFA) | REST / gRPC | axum / tonic | < 10ms | Medium |
| 18. Password Management Service | gRPC | tonic + argon2 | ~100ms (Intentional CPU hash) | Low |
| 19. Tenant Management Service | gRPC / REST | tonic / axum | < 10ms | Low |
| 20. Tenant Provisioning Service | Event-Driven | lapin (AMQP) | Asynchronous (Seconds) | Low Pipeline |
| 21. Tenant Lifecycle Management | gRPC | tonic | < 15ms | Low |
| 22. Tenant Isolation Service | Core In-Process | Static Lib Crate | < 0.1ms (Zero Network) | Bound to Core CPU |
| 23. Organization Management | GraphQL | async-graphql | < 15ms | Medium |
| 24. Workspace Management Service | GraphQL | async-graphql | < 12ms | Medium |
| 25. Team Management Service | GraphQL | async-graphql | < 10ms | Medium |
| 26. Group Management Service | GraphQL | async-graphql | < 10ms | Medium |
| 27. Membership Management | gRPC | tonic | < 5ms | High (Cached) |
| 28. Invitation Management Service | REST / GraphQL | axum / async-graphql | < 15ms | Low |
| 29. Role Management Service | gRPC | tonic | < 4ms | High (Cached) |
| 30. Permission Management Service | gRPC | tonic | < 3ms | Extreme (Cached) |
| ... | ... | ... | ... | ... |
| 146. Tenant Onboarding Automation | Event Workflow | temporal-sdk-core | Asynchronous Long-Running | Low Tasks |
| 147. Tenant Offboarding Service | Event-Driven | lapin | Asynchronous | Low |
| 148. Tenant Migration Service | Control Plane | tonic | Asynchronous Migration | Low Data Heavy |
| 149. Tenant Configuration Service | gRPC | tonic + mini-moka | < 1ms (Cached) | Extreme Read Volume |
| 150. Tenant Compliance Service | REST | axum | < 20ms | Low |