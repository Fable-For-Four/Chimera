---
description: Find the root cause of a bug and fix it, using the debugger agent
argument-hint: <what is broken, error text, or failing test>
---

Bug: $ARGUMENTS

1. Read `CLAUDE.md`. Anything in the locked list is off limits.
2. Use the **debugger** agent to reproduce the bug, find the root cause, and propose the smallest fix.
3. Show me the cause (`file:line`) and the proposed change.
4. **Stop and ask for my approval** before applying it.
5. After approval, apply the fix, add a test that fails without it, run `pytest -q` (plus `npm run build` in `web/` for UI fixes), and show the output.

Change only what the fix needs. No refactoring around it.
