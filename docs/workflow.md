# Workflow

## Full flow

```
   ┌─────────────────────────────────────────────────────────────┐
   │                    HUMAN kicks off                          │
   │    ./scripts/bootstrap.sh <module> <from> <to>              │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Phase 0 — Intake                                           │
   │  Human fills MIGRATION.md §0                                │
   │  Gate A                                                     │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Phase 1 — Research (AI, fresh context)                     │
   │  Input: prompts/01-research.md                              │
   │  Output: research.md                                        │
   │  Gate B — human reviews research                            │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Phase 2 — Plan (AI, fresh context)                         │
   │  Input: prompts/02-plan.md                                  │
   │  Output: plan.md                                            │
   │  Gate C — human reviews plan (THE main gate)                │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Phase 3 — Execute (AI, FRESH context per task)             │
   │  For each task T in plan.md:                                │
   │    - Paste prompts/03-execute-task.md with task ID          │
   │    - AI runs, commits, updates MIGRATION.md §3              │
   │    - Gate D passes                                          │
   │    - Start next task in NEW chat                            │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  Phase 4 — Verify (AI, fresh context)                       │
   │  Input: prompts/04-verify.md                                │
   │  Output: verification.md                                    │
   │  Gate E — human runs manual QA                              │
   └──────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
                         ┌─────────┐
                         │  DONE   │
                         └─────────┘
```

## Why "fresh context per task"

Large language models degrade as the context fills up. This is the single biggest reason AI-assisted migrations fail halfway through: by task 12, the model has 80k tokens of prior confusion in context and starts making mistakes it would never make fresh.

The recipe forces each Phase 3 task into a **new chat**, reading only:
- `MIGRATION.md`, `research.md`, `plan.md` (a few KB)
- The files listed in the task's "files touched" (a few KB)

Total context per task: tens of KB, not hundreds. The model stays sharp.

## Why phases are gated

Each gate exists because skipping it caused real pain:

- **Gate B** (no plan without finished research) — prevents planning based on wrong assumptions.
- **Gate C** (human review of plan) — the AI will always produce *a* plan; only a human knows if it matches what the migration actually needs.
- **Gate D** (per-task verify) — prevents "9 tasks passed, but task 3 silently broke task 7".
- **Gate E** (real DB upgrade) — the only gate that catches data-shape bugs, because they don't show up in isolated tests.
