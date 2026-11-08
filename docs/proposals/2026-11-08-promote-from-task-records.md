# Proposal: promote from task records

Outcome and Decisions sections in `docs/agent_logs/` could suggest updates to NOW and LEARNINGS for review. Suggestions should link the source and leave the final edit to a person or agent.

A CLI is repeatable but requires a separate invocation. CI can surface candidates on pull requests but may add noise and cannot judge what is durable. An explicitly invoked finish-task skill sees task context and can propose a focused diff; it depends on deliberate invocation. Recommend the finish-task skill first, with a reviewable diff and no automatic writes. Measure uptake before adding CLI or CI automation. This is a proposal only.
