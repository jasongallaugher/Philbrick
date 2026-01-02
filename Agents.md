# Agents.md - Multi-Agent Orchestration

## Goals

1. **Learn agentic/AI development techniques** - The process matters as much as the product
2. **Understand analog computing for LLM engineering** - Build intuition that transfers

---

## Model Tiers

| Tier | Models | Role |
|------|--------|------|
| **Expensive** | Opus, GPT-4o, Gemini Pro | Coordinate, validate, decide |
| **Moderate** | Sonnet, GPT-4o-mini | Complex tasks, judgment calls |
| **Cheap** | Haiku, Codex, Gemini Flash | Bulk work, code gen, simple edits |

### The Simple Rule

1. **Start Cheap** - Default for all code generation
2. **Escalate to Moderate** - If Cheap fails or task clearly needs judgment  
3. **Expensive never generates** - Only coordinates and validates

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Human                                  │
│  • Sets direction and pace              │
│  • Can interrupt or redirect            │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  EXPENSIVE (Lead - Opus)                │
│  • Coordinates, never writes code       │
│  • Dispatches to workers                │
│  • Validates results before reporting   │
└─────────────────────────────────────────┘
          │                   │
          ▼                   ▼
┌──────────────────┐  ┌──────────────────┐
│  CHEAP/MODERATE  │  │  CHEAP           │
│  (Workers)       │  │  (Validator)     │
│  • Write code    │  │  • Pass/fail     │
│  • Write tests   │  │  • Cite issues   │
└──────────────────┘  └──────────────────┘
```

---

## Token Discipline

### Expensive (Lead) Constraints

**NEVER:**
- Write code
- Generate file contents
- Produce implementation details

**ALWAYS:**
- Delegate code generation to workers
- Keep responses to 2-5 sentences for status
- 1-2 paragraphs max for explanations (when asked)

### Worker Constraints

**Input:** Only what's needed
- Relevant Outline.md section (not full doc)
- Files being modified (not full codebase)

**Output:** Only deliverables
```
FILES: [filename] (created|modified)
TESTS: [n] passed, [n] failed
ERRORS: [none | brief description]
```

No explanations unless explicitly requested.

### Validator Constraints

**Output only:**
```
VERDICT: PASS
```
or
```
VERDICT: FAIL
- [specific issue with file:line]
```

No suggestions, no alternatives.

---

## Validation

### When

| Trigger | Action |
|---------|--------|
| Every 2-3 steps | Light validation |
| Phase completion | Full validation |
| Worker error | Targeted review |

### Validator Prompt Template

```
You are a code reviewer. Be terse. No suggestions - just pass/fail.

CONTEXT: [Outline.md section for current step]
ACCEPTANCE: [From Outline.md checkpoint]
FILES: [Attach]
TESTS: [Paste output]

RESPOND ONLY WITH:
VERDICT: PASS or FAIL
[If FAIL: 1-3 bullets with file:line references]
```

### On Failure

1. Lead dispatches fix to worker with cited issues
2. Worker returns fixed files
3. Re-validate (max 2 retries, then escalate to human)

---

## Handoff Protocol

### Lead → Worker
```
TASK: [one sentence]
INPUT: [files/sections provided]
OUTPUT: [expected files]
ACCEPT: [1-2 line criteria]
```

### Worker → Lead
```
FILES: [list]
TESTS: [results]
ERRORS: [none or description]
```

---

## Pacing

**One step at a time.** The Outline.md defines discrete steps.

- Only work on current step
- Stop after completing a step
- Each step must be runnable and understandable

After each step, the human should be able to:
1. Run the code
2. See something happen
3. Understand what each part does

---

## Code Style

- **Simple over clever** - explicit, readable
- **Small files** - one thing per module
- **Type hints** - always
- **Docstrings** - brief, focus on purpose
- **TDD** - test core functionality, not exhaustive

---

## Anti-Patterns

- Don't front-load architecture (YAGNI)
- Don't optimize prematurely
- Don't add features beyond current step
- Don't skip checkpoints

---

## Communication

- Be concise
- No AI-isms ("Great question!", "I'd be happy to...")
- Ask when uncertain

---

## Reference

- **Outline.md** - What to build and in what order
- **sketch.py** - Initial proof-of-concept (reference only)
