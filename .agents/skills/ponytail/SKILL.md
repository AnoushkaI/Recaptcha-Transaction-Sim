---
name: ponytail
description: Enforces minimal lines of code, standard Python library usage, zero bloat, and lightweight function signatures. Prevents introduction of unnecessary class abstractions or unrequested npm/pip packages.
---

# Ponytail Principle — Code Minimalism Enforcement

## Rules

1. **Standard Library First**: Use `json`, `dataclasses`, `random`, `datetime`, `uuid`, `hashlib`, `sqlite3` — no third-party packages unless explicitly requested.
2. **No Unnecessary Abstractions**: Avoid factory patterns, registry patterns, or base-class hierarchies unless the domain clearly demands them.
3. **Flat Function Signatures**: Prefer `def fn(a, b, c)` over `def fn(config: MyConfigObject)`.
4. **No Over-Engineering**: A 10-line function is better than a 100-line class for simple operations.
5. **Zero Bloat Imports**: Do not import libraries unused in the current module.
6. **Lean Session State**: Store only the minimum state required — avoid caching redundant copies.
7. **Inline Comments Only Where Necessary**: Do not add verbose docstrings to every private helper.
8. **Streamlit Widgets Only**: Use standard Streamlit widgets — no custom JS components or external UI libraries.

## Checklist Before Writing Code

- [ ] Can this be done with stdlib? (yes → use stdlib)
- [ ] Is there an existing utility in this repo that does this? (yes → reuse it)
- [ ] Does this class need `__init__`, or can it be a module-level function? (function preferred)
- [ ] Is every import actually used in the file?
