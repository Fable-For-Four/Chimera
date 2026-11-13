---
description: Pre-submission check. Security (deployment agent) and desktop layout (uiux agent), before anything is merged or submitted
argument-hint: (optional) what to focus on
---

Run all checks before submission so nothing breaks at the end. Focus: $ARGUMENTS

1. Read `CLAUDE.md`. **FAILSAFE:** do not change, reformat or "fix" any locked part, or anything I have said is working.
2. Run `pytest -q`, then `npm run lint` and `npm run build` in `web/`. If any of them fails, stop and report it.
3. Run the **deployment** agent and the **uiux** agent in parallel:
   - deployment: `.gitignore`, `.env` safety, leaked secrets in code and history, sign-in and cookie setup, clean-clone run, the PLAN.md section 13 checklist.
   - uiux: layout at 1920x1080 and 2560x1440, aspect ratio, no hardcoded numbers, the empty and error states, readability.
4. Combine their results into one list, most serious first, each with its exact fix.
5. **Stop and ask for my approval** before changing any file. This command only reports.

Final line: **Ready to deploy** or **Not ready**, with the blocking items.
