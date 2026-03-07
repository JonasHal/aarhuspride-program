# Development Conventions

## Philosophy

- **Simplicity is king** — the simplest solution that works is the best solution
- **Self-documenting code** — if it needs comments, refactor it
- **Functional over OOP** — pure functions, composition, immutability
- **Commit early, commit often** — small, focused, verified commits

---

## Cross-Language Design Principles

These rules apply **to all languages**, regardless of tooling.

### Code Design
- Prefer **pure functions** where feasible; isolate side effects.
- Organize code so changes are easy and predictable.
- Avoid hidden state and mutable globals.

### Types & Data
- Declare types explicitly at *module boundaries*.
- Use language-specific type features to model domain constraints (e.g., Rust enums, TS `zod` schemas).

### Error Handling
- Treat errors as structured data, not control flow.
- **Catch specific exceptions**, never bare `except:` or `except Exception:` unless re-raising.
- Add contextual information when propagating errors.
- Avoid swallowing errors silently.
- Let unexpected errors crash — they reveal bugs. Only catch what you can handle.

### Testing
- Prefer **unit tests** for pure logic and **integration tests** for I/O boundaries.
- Assert behavior, not implementation details.
- Aim for reproducibility and determinism.
- Use **AAA pattern** (Arrange, Act, Assert):
  ```python
  def test_user_creation():
      # Arrange
      name = "Alice"
      
      # Act
      user = create_user(name)
      
      # Assert
      assert user.name == name
  ```

### Comments & Docs
- Use comments to explain *why*, never *what* — if you need a "what" comment, rename or refactor instead.
- Bad: `timeout = 30  # API timeout in seconds`
- Good: `API_TIMEOUT_SECONDS = 30`
- Public APIs must have documentation; internal helper functions usually do not.
- If code needs lots of comments, **refactor** instead.

### Git & Collaboration
- Use a *feature-branch workflow* with clear naming (e.g., `feat/…`, `fix/…`, `refactor/…`).
- Rebase or squash commits to maintain clean history.
- Use PRs with reviews, tests, and clear descriptions.

### Architecture & Boundaries
- Divide code into *layers* (core logic, side effects, interfaces).
- Keep modules small and focused.
- Separate business logic from runtime and framework concerns.

---

## Layered Architecture

### Core Principles

**1. Dependencies Flow One Direction**

If A → B → C, then C can import B and A, but A cannot import C. This single rule eliminates circular imports entirely.

**2. Leaf Modules Are Your Foundation**

Modules with zero internal imports are the most stable. Put shared types, constants, and pure data structures here. Everything else builds on top.

**3. Group by Reason to Change**
- Data shapes change when contracts change
- Clients change when external APIs change
- Business logic changes when requirements change
- Interfaces change when consumers change

Same reason to change = same module.

**4. Configuration Sits Low**

Config should be readable by all layers but depend on nothing. When config imports business logic, you've inverted the hierarchy.

**5. Ports and Adapters Emerge Naturally**
- **Core**: types, business logic (pure, no I/O)
- **Adapters**: clients (outbound), servers (inbound)
- **Entry points**: CLI, main functions

The core doesn't know how it's called or what it calls.

**6. Comments Signal Missing Structure**

Section dividers and "what" comments often mean the file is doing too much. Clear module boundaries make code self-documenting.

**7. Name Layers by Role, Not Technology**

`services/` not `openai/`. `client.py` not `http.py`. Roles are stable; technologies change.

---

## Project Structure

```
src/program/
├── __init__.py          # Public API exports
├── client.py            # External API client (Trustpilot REST API)
├── settings.py          # Configuration (pydantic-settings, env vars)
├── types.py             # Domain models + response types
├── cli/
│   └── agent.py         # Interactive CLI tools
├── mcp/
│   └── server.py        # MCP server (tool definitions)
└── services/
    ├── analysis.py      # AI/LLM integration (Azure OpenAI)
    └── reviewer.py      # Business logic (LangGraph agents)

tests/                   # Mirror src structure
```

### Layer Responsibilities

| Layer | Purpose | Dependencies |
|-------|---------|--------------|
| `types.py` | Domain models, response schemas | None (leaf module) |
| `settings.py` | Configuration loading | pydantic-settings |
| `client.py` | External API calls | settings, types |
| `services/` | Business logic, AI integration | client, settings, types |
| `mcp/` | Tool exposure via MCP protocol | services, client, types |
| `cli/` | User-facing CLI tools | services, mcp |

### Import Rules

- **Absolute imports only**: `from trustpilot.types import Review`
- **No circular imports**: lower layers cannot import from higher layers
- **types.py is a leaf**: no internal imports allowed

---

## Python

### Tools
| Tool | Purpose | Install |
|------|---------|---------|
| `uv` | Package/project manager, Python versions | `brew install uv` |
| `ruff` | Linter & formatter | `uv tool install ruff` |
| `ty` | Type checker (Astral, 10-100x faster than mypy) | `uv tool install ty` |
| `pytest` | Testing | `uv add --dev pytest` |

### Workflow
```bash
uv init myproject && cd myproject
uv add requests
uv add --dev pytest

uv run python script.py
uv run pytest

# One-off (no install)
uvx ruff check .
uvx ty check .
```

### Before Commit

Run the verification loop:
```bash
uvx ruff format .
uvx ruff check --fix .
uvx ty check .
uv run pytest
```

**Pre-commit checklist** (all must pass):
- [ ] `ruff format .` — no files reformatted
- [ ] `ruff check .` — no errors
- [ ] `ty check .` — all checks passed  
- [ ] `pytest` — all tests passed
- [ ] No obvious comments (code should be self-documenting)
- [ ] No section divider comments (`# ====...`)
- [ ] Comments explain *why*, not *what*

### Style
```python
async def fetch_users(user_ids: list[int]) -> list[User]:
    """Fetch users by their IDs."""
    async with httpx.AsyncClient() as client:
        tasks = [client.get(f"/users/{id}") for id in user_ids]
        responses = await asyncio.gather(*tasks)
        return [User(**r.json()) for r in responses]
```

- Type annotations: always, Python 3.12+ (`list[T]`, `X | None`)
- Docstrings: brief, public APIs only
- Async for I/O

---

## Git

### Commit Format
```
type: short description
```

| Type | Use |
|------|-----|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `chore:` | Maintenance |
| `refactor:` | Restructure (no behavior change) |
| `test:` | Tests |

### Pull Requests
- **Title**: same format as commits (`type: description`)
- **Description**: explain the *why*, not just the *what*
- **Before/after**: show output changes when relevant
- **Link issues**: reference related issues/discussions
- Keep PRs focused—one logical change per PR

---

## Quick Reference

| Lang | Format | Lint | Type Check | Test |
|------|--------|------|------------|------|
| Python | `ruff format .` | `ruff check --fix .` | `ty check .` | `pytest` |

---

**The Loop:** Change → Verify → Commit → Repeat

If it's not tested, it's not done.
