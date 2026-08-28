Research, plan and implement a change end to end, locally, without touching anything remote.

- **Target**: `$1`
- **Goal or issue**: `$2`
- **Related paths (optional)**: `$3`

If `$1` or `$2` is empty, ask for it and stop. Do not guess the target or invent the goal.

## 1. Research before forming an opinion

Read the target as if you had never seen it. Do not answer from memory: what you recall about
this codebase may be stale or may belong to a different project.

- Trace the real flow end to end: every file the change touches, every caller of every function
  you plan to modify. `grep` for callers before deciding where a fix belongs.
- Read the change proposals that already govern this area (OpenSpec changes, ADRs, RFCs, design
  docs) and follow them. If your plan would contradict one, say so explicitly instead of
  quietly diverging.
- Read the related paths in `$3` and the docs that describe how they connect to the target.
- Check the tests that already cover this area. They tell you the intended behaviour more
  reliably than prose does.
- Look up external dependencies and APIs you are not certain about rather than assuming their
  shape.

Finish this phase by writing down what you now know that you did not know before, and every
question still open. An open question that would change the implementation is a reason to ask,
not a reason to pick one branch and hope.

## 2. Plan to a written acceptance list

Produce a plan whose completion is checkable by someone else:

- A numbered list of changes, each naming the file and what changes in it.
- For each item, the acceptance criterion: the observable behaviour that proves it works.
- The tests to add or extend, named, with the case each one pins down. Cover the edge cases you
  found in phase 1, not a generic happy path.
- What is deliberately out of scope, and why.

"100% coverage" is not a criterion, it is a wish. Replace it with cases you can point at.

Then reread the plan with fresh eyes, specifically looking for: a step that assumes something
phase 1 did not verify, a file you are about to change without having read its callers, and an
acceptance criterion that cannot actually fail.

## 3. Implement locally

- **Branch first, and only from a clean tree.** If the working tree is dirty, stop and report
  what is uncommitted: a branch created over someone else's uncommitted work carries that work
  along and hides it. Never stash or commit changes you did not make.
- Leave your own changes **uncommitted** on that branch.
- **Nothing remote.** No `git commit`, no `git push`, no PR or MR, no deploy, no writes to a
  live environment or a shared service, no destructive command. Reading remote state is fine.
- Match the surrounding code: its naming, its error handling, its comment density. A change
  that reads as foreign is a change the next person distrusts.
- Run the tests you added and the suite around them. If something fails, fix it or report the
  failure with its output. Never describe untested code as working.

## 4. Report

Reread your own diff with fresh eyes before writing the recap, and state plainly anything you
left incomplete.

Write in full sentences, structured as:

1. **What changed**: the files you created or modified and the logic in each.
2. **Why**: the reasoning behind the design choices you made, and the alternatives you
   rejected.
3. **Verification**: what you ran and what it reported. Quote failures rather than
   summarising them away.
4. **What is left**: how to test this locally, what you deliberately did not do, and the open
   questions a human still has to answer.

If any part of the goal turned out to be blocked, finish everything else and say exactly what
you left out and why. Narrowing the scope on your own is not your call to make silently.
