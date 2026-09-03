# Decision Registry

The lifecycle is `proposed` → `accepted` → `superseded` | `rejected`. Only
accepted decisions define current direction. Use stable IDs such as `D-001` and
link detailed records from `decisions/` when the evidence or trade-offs need
more space; a detail record carries the six required frontmatter keys, while
this registry stays plain Markdown.

## D-000: Example decision

- Status: `proposed`
- Date: YYYY-MM-DD
- Decision: Replace this example with a decision that constrains future work.
- Rationale: Explain why this choice is being considered.
- Consequences: Describe benefits, costs, and follow-up obligations.
- Evidence: Link to a design, task, primary artifact, review, result,
  incident, or external source. Pin a repository path to the state it cites:
  `path/to/file@<commit>`.
