---
description: Read a requirement and write its test cases first, using the tester agent
argument-hint: <task ID or PLAN.md section, e.g. "A2" or "6.2 Sort">
---

Feature: $ARGUMENTS

1. Read `CLAUDE.md` (locked parts, ownership) and the matching task and spec in `PLAN.md`. Note the task's time slot in section 8.
2. Restate the requirement in 3 to 6 short bullets, including its **Done when** line.
3. Use the **tester** agent to write the tests in `tests/` and run them. They should fail for now, because the feature is not built yet.
4. Show me the bullets, the test names and the test output.
5. **Stop and ask for my approval** before writing any feature code.

Touch only the files the task owns. Never touch locked parts.
