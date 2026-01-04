# Agents.md - Multi-Agent Orchestration

## Goals

1. **Learn agentic/AI development techniques** - The process matters as much as the product
2. **Understand analog computing for LLM engineering** - Build intuition that transfers

---

## Model Tiers

| Tier | Examples | Role |
|------|----------|------|
| **Expensive** | High-capability models (top-tier GPT, Claude, Gemini, etc.) | Coordinate, validate, decide |
| **Moderate** | Mid-tier models | Complex tasks, judgment calls |
| **Cheap** | Fast/lightweight models | Bulk work, code gen, simple edits |

**Note:** Model selection should be based on capability tiers rather than specific model names. Choose models from your provider that match the tier requirements.

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
│  EXPENSIVE (Lead)                       │
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

## Tooling

### Environment Setup

**Before starting any work, verify the environment:**

1. **Check `uv` is available:**
   ```bash
   uv --version
   ```
   If not found, install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

2. **Verify Python environment:**
   ```bash
   uv run python --version
   ```
   Should show Python 3.11+ (per `pyproject.toml` requirements)

3. **Sync dependencies:**
   ```bash
   uv sync
   ```
   This creates/updates the virtual environment and installs all dependencies from `pyproject.toml`

4. **Verify installation:**
   ```bash
   uv run python -c "import textual; import pytest; print('OK')"
   ```

### Command Patterns

**Always use `uv` - never raw Python/pip/pytest commands.**

| Task | Command | Notes |
|------|---------|-------|
| Run Python script | `uv run python script.py` | Never use `python script.py` |
| Run module | `uv run python -m module.name` | |
| Run main entry point | `uv run main.py` | |
| Run tests | `uv run pytest` | Never use `pytest` directly |
| Run tests (specific) | `uv run pytest tests/test_file.py::test_function` | |
| Install package | `uv add package-name` | Adds to `pyproject.toml` |
| Install dev package | `uv add --dev package-name` | |
| Sync environment | `uv sync` | Updates venv from `pyproject.toml` |
| Check Python version | `uv run python --version` | |
| Interactive Python | `uv run python` | Never use `python` directly |

### Sandbox Considerations

**In sandboxed environments (like Cursor's terminal):**

- `uv` manages the virtual environment automatically - no need to activate manually
- Always use `uv run` prefix for all Python commands
- If `uv run` fails with "command not found", verify `uv` is in PATH
- The virtual environment is typically in `.venv/` or `venv/` (check `pyproject.toml` or `uv.toml`)

### Troubleshooting

**If `uv run python` fails:**
1. Run `uv sync` to ensure environment exists
2. Check `uv run python --version` works
3. Verify `pyproject.toml` exists and is valid

**If imports fail:**
1. Run `uv sync` to install dependencies
2. Verify with `uv run python -c "import <module>"`

**If tests fail to run:**
1. Ensure using `uv run pytest`, not `pytest`
2. Check `pytest` is in dependencies (it should be in `pyproject.toml`)

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
