# enterprise-agent-governance

Policy enforcement and audit layer for multi-agent pipelines.

**Status: in active development.** Built as a self-directed study project.

## What this is

Most agent observability tooling (Langfuse, Arize Phoenix, LangSmith) answers
*what did the agent do*. This project addresses the adjacent, less-built layer:
*what is the agent allowed to do, and can you prove what happened*.

Scope:
- Tamper-evident run traces aligned to OpenTelemetry GenAI semantic conventions
- Declarative policy file gating tool and model calls (allow / block / require-approval)
- Token budget circuit breaker
- Human-in-the-loop approval gates on high-risk actions
- Adversarial probe suite testing the policy layer
- CLI for reconstructing why a given run behaved as it did

Governs the pipeline in
[adk-vendor-snapshot](https://github.com/snehhilgupta/adk-vendor-snapshot),
coupled through a trace format rather than a code dependency.

## Design notes

Full design documentation to follow.
