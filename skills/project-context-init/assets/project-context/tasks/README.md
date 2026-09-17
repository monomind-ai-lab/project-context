# Task records

Use this directory for durable plans, progress, validation, and handoffs.
Agents create records with `project-context record --kind task` and update the
same record as work advances. Completed task records are historical evidence;
current status must be promoted to `../NOW.md`.

Every record here carries the six required frontmatter keys — `id`, `kind`,
`status`, `title`, `created`, `asserted_by` — as `TEMPLATE.md` shows.
