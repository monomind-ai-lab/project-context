# Create a private Context Hub

Use this prompt with an AI agent that can read and write the local destination
folder. It creates and validates local files only; private Git hosting remains a
separate, deliberate human-controlled step. Applying the current hardened
runtime requires macOS or Linux; Windows can preview and inspect, but mutation
commands deliberately fail closed before writing.

```text
Create a Project Context Hub for me using
https://github.com/monomind-ai-lab/project-context.

First read and follow `skills/context-hub/SKILL.md` from that repository. Treat
Markdown and Git as the storage contract: do not add a database, vector store,
server, or required Obsidian dependency. Obsidian may be an optional client and
Graphify may be an optional derived index, but neither is authoritative.

Before writing:
1. Inspect the local destination and explain the proposed trust boundary. One
   hub is one read-access domain; projects that must not see one another belong
   in separate hubs.
2. Ask only for information that cannot be inferred safely: the destination,
   whether this will be opened in Obsidian, and the first stable human or agent
   actor ID, display name, and kind. If I want an initial project, also ask for
   its stable project ID and purpose. If its work lives outside the Hub, ask for
   a hub-wide binding ID and the existing local Git checkout or folder path.
3. Show the exact create-only plan. Preserve every existing file, Git setting,
   Obsidian setting, and agent instruction unless I explicitly approve a merge.
4. Run `project-context hub init --target <path> --dry-run` and show me its
   result. Wait for my approval before applying it.

After approval, ensure the target is an existing local directory, use
`project-context hub init --target <path> --apply`, then use
`project-context hub add-actor` and `project-context hub add-project` for only
the records I approved, attributing project creation with `--created-by`. For an
approved external workspace, use `project-context hub bind-project`; keep its
absolute path only in ignored `.context-hub/local.yaml` and portable metadata
in the project's `PROJECT.md`. Allow the initializer to create or update its
single delimited thin-pointer block in both root
`AGENTS.md` and `CLAUDE.md`, preserving every other byte; do not duplicate the
full protocol in either file. Tracked references must be portable.

Run `project-context hub doctor --target <path>` after creation and report any
warnings. Do not create a
remote repository, call a hosting API, invite collaborators, push, publish,
enable a second sync service, or store credentials. Report exactly which local
bindings were created. Do not claim that the CLI cloned or fetched a remote, or
that it verified cross-repository drift: those remain explicit repository
operations. Before enabling semantic Graphify extraction, ask me to approve a
model provider suitable for the source classification. Stop after local
validation and give me the reviewable local path plus the separate manual steps
I may choose later for a private remote.
```
