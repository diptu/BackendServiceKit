---
name: engineering-auditor
description: Performs a comprehensive repository audit by evaluating the codebase against all installed engineering skills and producing a production-readiness report with prioritized recommendations.
---

# Goal

Perform a complete engineering review of the repository.

Assume every installed Claude Skill defines an engineering standard.

Evaluate the repository against every applicable skill.

Do not implement code unless explicitly requested.

Instead, produce an actionable engineering assessment.

---

# Audit Process

## Phase 1

Understand the repository.

Review:

- project structure
- architecture
- technologies
- dependencies
- documentation
- configuration
- tooling

---

## Phase 2

Determine which skills are applicable.

Examples:

- Next.js
- NestJS
- TypeScript
- Tailwind
- PostgreSQL
- Docker
- Kubernetes
- DevOps
- Security
- Testing
- AI
- MLOps
- Architecture
- Documentation

Skip skills that are not relevant to the repository.

---

## Phase 3

Evaluate the repository against EVERY applicable skill.

Each skill should answer:

- Are best practices followed?

- What is missing?

- What is incorrect?

- What can be improved?

- What production practices are absent?

---

## Phase 4

Cross-skill validation.

Identify inconsistencies between domains.

Examples:

- frontend violates backend contracts

- API documentation outdated

- database schema inconsistent

- authentication incomplete

- CI/CD missing

- monitoring absent

---

# Evaluation Categories

Evaluate every applicable area.

## Architecture

- Clean Architecture
- SOLID
- Modular Design
- Separation of Concerns
- Scalability

Score 0–10.

---

## Frontend

Review:

- React
- Next.js
- TypeScript
- Tailwind
- Accessibility
- Performance
- SEO

---

## Backend

Review:

- NestJS
- FastAPI
- API Design
- Authentication
- Authorization
- Validation
- Error Handling

---

## Database

Review:

- Schema
- Indexing
- Constraints
- Migrations
- Performance

---

## Security

Review:

- OWASP
- JWT
- Secrets
- RBAC
- Input validation

---

## Testing

Review:

- Unit tests

- Integration tests

- E2E tests

- Coverage

---

## DevOps

Review:

- Docker

- CI/CD

- Infrastructure

- Monitoring

- Logging

---

## Documentation

Review:

- README

- Architecture docs

- ADRs

- API documentation

---

## Code Quality

Review:

- Naming

- Folder structure

- Type safety

- Dead code

- Duplication

- Complexity

---

## Performance

Review:

- Rendering

- Queries

- Caching

- Bundle size

- Database

---

# Production Readiness

Provide scores.

| Category | Score |
|----------|------|
| Architecture | /10 |
| Code Quality | /10 |
| Security | /10 |
| Testing | /10 |
| Performance | /10 |
| DevOps | /10 |
| Documentation | /10 |
| Scalability | /10 |
| Maintainability | /10 |

Overall Score:

XX/100

---

# Findings

Categorize findings.

## Critical

Issues that should be fixed immediately.

---

## High

Important production concerns.

---

## Medium

Engineering improvements.

---

## Low

Minor cleanup.

---

# Missing Features

List production features that should exist but do not.

---

# Technical Debt

Identify architectural debt.

Estimate impact.

---

# Best Practice Violations

Reference the engineering principle violated.

Explain why.

Recommend a solution.

---

# Refactoring Opportunities

Identify reusable abstractions.

Reduce duplication.

Improve maintainability.

---

# Prioritized Roadmap

Produce an implementation roadmap.

Priority 1

Priority 2

Priority 3

Priority 4

---

# Deliverables

Always provide:

1. Executive Summary

2. Repository Health Score

3. Production Readiness Score

4. Strengths

5. Weaknesses

6. Missing Features

7. Technical Debt

8. Security Findings

9. Performance Findings

10. Testing Gaps

11. Documentation Gaps

12. Architecture Review

13. Refactoring Opportunities

14. Implementation Roadmap

15. Final Recommendations

---

# Guiding Principles

Be objective.

Prefer evidence over assumptions.

Prioritize production-grade engineering.

Do not recommend unnecessary complexity.

Focus on maintainability, scalability, security, developer and user experience.