# Detailed decisions

Use this directory for every durable decision that constrains future work.
Agents create records with `project-context record --kind decision`; it assigns
the stable ID and links the detail from `../DECISIONS.md`.

Every record here carries the six required frontmatter keys — `id`, `kind`,
`status`, `title`, `created`, `asserted_by` — as `TEMPLATE.md` shows. Nothing
else is required, and an absent optional field is simply absent.
