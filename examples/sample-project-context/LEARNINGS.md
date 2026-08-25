# Learning Registry

## L-001: Test time boundaries explicitly

- Status: `accepted`
- Scope: expiring authentication tokens
- Learning: Happy-path tests do not protect expiry, clock-skew, and replay boundaries.
- Action: Cover just-before, exact-boundary, just-after, and replay cases.
- Evidence: Regression reproduced at the expiry boundary and fixed by explicit comparison semantics.
