# Simplified IAM + ABAC Multi-Tenant SaaS Example

## Tenant → Organization Hierarchy

```text
SaaS Platform
│
├── Alphabet (Tenant)
│   ├── Google Search (Organization)
│   ├── YouTube (Organization)
│   └── DeepMind (Organization)
│
└── Meta (Tenant)
    ├── Facebook (Organization)
    ├── Instagram (Organization)
    └── WhatsApp (Organization)
```

---

# Tenant Table

| Tenant ID | Tenant Name |
|------------|------------|
| tenant_alphabet | Alphabet |
| tenant_meta | Meta |

---

# Organization Table

| Organization ID | Organization | Tenant |
|-----------------|-------------|---------|
| org_search | Google Search | Alphabet |
| org_youtube | YouTube | Alphabet |
| org_deepmind | DeepMind | Alphabet |
| org_facebook | Facebook | Meta |
| org_instagram | Instagram | Meta |
| org_whatsapp | WhatsApp | Meta |

---

# Users

| User | Tenant | Organization |
|--------|---------|-------------|
| Sundar | Alphabet | Google Search |
| Neal | Alphabet | YouTube |
| Demis | Alphabet | DeepMind |
| Mark | Meta | Facebook |
| Adam | Meta | Instagram |
| Will | Meta | WhatsApp |

---

# Roles

| Role | Description |
|--------|-------------|
| Owner | Full tenant access |
| Admin | Manage users/resources |
| Manager | Manage organization resources |
| Member | Standard user |
| Auditor | Read-only access |

---

# Memberships

| User | Organization | Role |
|--------|-------------|--------|
| Sundar | Google Search | Owner |
| Neal | YouTube | Admin |
| Demis | DeepMind | Manager |
| Mark | Facebook | Owner |
| Adam | Instagram | Admin |
| Will | WhatsApp | Member |

---

# Resources

| Resource | Type | Organization |
|-----------|--------|-------------|
| search_config_001 | Search Configuration | Google Search |
| video_policy_001 | Video Policy | YouTube |
| model_001 | AI Model | DeepMind |
| page_001 | Facebook Page | Facebook |
| reel_001 | Reel | Instagram |
| channel_001 | Business Channel | WhatsApp |

---

# Permissions

| Permission |
|------------|
| user:create |
| user:update |
| resource:view |
| resource:create |
| resource:update |
| resource:delete |
| report:view |
| audit:view |

---

# Role → Permission Mapping

| Role | Permissions |
|--------|------------|
| Owner | All |
| Admin | User + Resource Management |
| Manager | Resource Management |
| Member | Resource View |
| Auditor | Report View + Audit View |

---

# User Attributes (ABAC)

| User | Department | Location |
|--------|-----------|----------|
| Sundar | Search | USA |
| Neal | Media | USA |
| Demis | AI Research | UK |
| Mark | Social | USA |

---

# Resource Attributes

| Resource | Classification |
|----------|---------------|
| search_config_001 | Confidential |
| video_policy_001 | Internal |
| model_001 | Restricted |
| reel_001 | Public |

---

# Example ABAC Policies

## DeepMind AI Model Policy

```text
ALLOW model:update

IF

organization = DeepMind

AND

department = AI Research

AND

mfa_verified = true
```

## YouTube Policy

```text
ALLOW video_policy:update

IF

organization = YouTube

AND

role IN [Owner, Admin]
```

## Instagram Policy

```text
ALLOW reel:update

IF

organization = Instagram

AND

resource.classification != Restricted
```

---

# Authorization Example

Demis tries to update an AI model.

```text
User: Demis
Organization: DeepMind
Role: Manager
Action: model:update
```

Authorization Engine:

```text
Tenant Match?                 ✓
Organization Match?           ✓
Role Permission?              ✓
Department = AI Research?     ✓
MFA Verified?                 ✓

Decision: ALLOW
```

---

# Final Simplified IAM Structure

```text
Platform
│
├── Alphabet (Tenant)
│   ├── Google Search
│   │    ├── Users
│   │    └── Resources
│   │
│   ├── YouTube
│   │    ├── Users
│   │    └── Resources
│   │
│   └── DeepMind
│        ├── Users
│        └── Resources
│
└── Meta (Tenant)
    ├── Facebook
    │    ├── Users
    │    └── Resources
    │
    ├── Instagram
    │    ├── Users
    │    └── Resources
    │
    └── WhatsApp
         ├── Users
         └── Resources

Roles
 └── Permissions

Policies
 ├── User Attributes
 ├── Resource Attributes
 └── Environment Attributes
```

## Key Concepts

- Tenant = Customer Account (Alphabet, Meta)
- Organization = Business Unit/Product (YouTube, DeepMind, Instagram, etc.)
- Users belong to Organizations
- Roles grant Permissions (RBAC)
- Policies enforce conditions (ABAC)
- Resources belong to Organizations
- Tenant remains the primary security boundary
