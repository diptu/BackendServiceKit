
# Multi-Tenant SaaS + IAM + ABAC platform Hierarchy


```mermaid
flowchart TD
    T[Tenant]
    O[Organization]
    W[Workspace]
    G[Groups]
    TM[Team]
    M[Members]
    R[Resources]

    T --> O
    O --> W
    O --> G

    W --> TM
    W --> R

    TM --> M
```


