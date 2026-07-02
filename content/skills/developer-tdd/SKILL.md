# Test-Driven Development Discipline

Red-green-refactor as a working discipline, not a slogan. Use it to keep changes small, verified, and reversible — not as a rule to follow when it doesn't fit the problem.

## The Cycle

1. **Red** — write a test for behavior that doesn't exist yet. Run it. Watch it fail, and read *why* it failed — a test that fails for the wrong reason (import error, typo) proves nothing yet.
2. **Green** — write the minimum code to pass that test. Resist the urge to also handle the next three cases you can already see coming; that's the next cycle.
3. **Refactor** — with the test passing, clean up: rename, extract, remove duplication. Re-run the test after every change. If a refactor needs new behavior, that's a new red step, not a shortcut inside this one.

Repeat. Each cycle should take minutes, not hours. If red-green-refactor for one piece of behavior is taking longer than that, the slice is too big — split it.

## Keeping Cycles Small

- One assertion of intent per cycle. "Handles empty input" and "handles null input" are two cycles, not one test with two assertions bolted together.
- If the next obvious step is un-typeable in one sentence ("test that X returns Y when Z"), it's not one cycle yet — break it down further.
- Commit-sized thinking: each green state is a point you could stop and ship. If you can't describe what would be lost by stopping here, the cycle was scoped correctly.
- Prefer many small red-green-refactor loops over one large one that front-loads a big test file before any code exists — that's test-after wearing a TDD costume, and it loses the design-feedback benefit TDD is for.

## What TDD Is Actually For

The discipline exists to get fast feedback on design, not to hit a coverage number. Writing the test first forces you to use the interface before you've committed to its implementation — awkward call sites reveal awkward APIs while they're still cheap to change. If a test is hard to write, that's signal about the code under test, not a reason to skip straight to the implementation and backfill.

## When to Skip It

TDD is a tool for a specific kind of uncertainty — logic with clear inputs/outputs that you don't yet trust yourself to get right on the first pass. It's not free everywhere:

- **Exploratory/throwaway code** — spikes, prototypes, one-off scripts you'll delete. Writing tests first for code whose shape you don't know yet just slows down the exploration. Test it after, if it survives.
- **Pure plumbing** — wiring, config, glue code with no branching logic. A test here mostly re-asserts the wiring exists; it doesn't catch the failure modes that matter (those show up at integration, not unit, level).
- **UI/visual work** — layout and styling are usually better verified by looking at the rendered result than by asserting on DOM structure. Don't force a red-green cycle onto something a human eye checks in two seconds.
- **Already-battle-tested paths** — extending a well-covered module rarely needs a fresh TDD cycle for a two-line addition if the existing suite already exercises the surrounding behavior; add a focused regression test instead (see the `developer-diagnosing-bugs` skill for the same idea applied to bug fixes).

Skipping TDD is a judgment call, not a shortcut to take by default. Default to red-green-refactor for anything with real logic; skip deliberately, not out of impatience.

## Anti-Patterns to Flag

- Writing all the tests for a feature up front, then all the implementation — loses the tight feedback loop, and the resulting tests tend to mirror the implementation rather than the intended behavior.
- A "red" step that never actually ran red — the test was written against code that already existed. That's test-after with extra steps.
- Skipping refactor because the code is green — the discipline is red-green-**refactor**; skipping the third step is how test suites end up locking in bad design.
- Tests that assert implementation details (private method calls, internal state) instead of observable behavior — they make refactor steps break tests that shouldn't have needed to change.
