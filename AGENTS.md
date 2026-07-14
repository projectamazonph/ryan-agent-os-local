# Development Contract

## Method

Use Test-Driven Development and Loop Engineering for every behavior change:

1. Add or update a failing test.
2. Make the smallest implementation change that passes.
3. Run the focused test.
4. Run the complete test suite.
5. Refactor only while tests remain green.
6. Record material failures and decisions.

## Required checks

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m compileall -q src
```

## Design constraints

- Python 3.11+ standard library only at runtime.
- Never store secret values in Ryan Agent OS files or SQLite.
- Preserve existing unmanaged Git hooks unless explicitly forced.
- Avoid unbounded filesystem traversal.
- Never silently bypass validation or protected-branch checks.
- Keep repository contracts human-readable and machine-executable.
- Errors must identify the blocked action and the next safe correction.
