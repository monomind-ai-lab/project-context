# Decision Registry

## D-001: Use passwordless email login

- Status: `accepted`
- Date: 2026-08-05
- Decision: Use emailed sign-in links instead of repository-owned passwords.
- Rationale: Reduce credential-handling scope and recovery complexity.
- Consequences: Link expiry and replay behavior require focused tests.
- Evidence: Accepted authentication design and passing integration tests.
