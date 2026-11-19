---
type: llm
focus: trace
weight: 1
---

The response independently verifies exact PR/source CI despite missing run
associations, resolves drafts from validated creation IDs, and tests actual CLI
binary framing/content length and redacted stderr rather than relying solely on
mocked HTTP success or blind retries.
