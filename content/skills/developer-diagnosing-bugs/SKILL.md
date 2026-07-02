# Diagnosing Bugs

A structured loop for local debugging: reproduce, minimize, hypothesize, instrument, fix, regression-test. Use it in place of guessing-and-checking, especially once the first two or three guesses haven't landed.

## The Loop

### 1. Reproduce

Get the failure to happen on demand, in the smallest environment that still shows it. A bug you can't reliably reproduce isn't ready to debug yet — everything after this step wastes time without a reliable "did that fix it?" signal.

- Capture the exact input, command, or sequence of actions that triggers it.
- If it's intermittent, find what varies between the runs that fail and the runs that don't (timing, ordering, concurrency, external state) before moving on — intermittent bugs usually mean a hidden variable, not bad luck.

### 2. Minimize

Strip the reproduction down to the smallest case that still fails. Remove unrelated code, data, and configuration one piece at a time, re-checking the failure still happens after each removal.

- A minimal repro is also a fast repro — you want the shortest possible loop for the hypothesize/instrument/fix cycle below.
- Minimizing often finds the bug by itself: the point where removing something makes the failure disappear is a direct pointer at what's involved.

### 3. Hypothesize

Form a specific, falsifiable hypothesis about the cause — not "something's wrong with the parser" but "the parser drops the last token when the input doesn't end in a delimiter." A hypothesis you can't imagine being wrong isn't specific enough yet.

- Rank hypotheses by how cheaply they can be checked, not just by how likely they seem — a 30-second check that rules out a plausible cause is worth more than staring at the code guessing.
- Write the hypothesis down (even just in your head deliberately) before testing it. This is what separates the loop from unstructured poking — it forces prediction before observation.

### 4. Instrument

Test the hypothesis directly: a log line, a debugger breakpoint, a temporary assertion, a smaller unit test that isolates the suspected component. Prefer the tool that gives the fastest answer for this specific hypothesis, not whichever one is already open.

- If the instrumentation confirms the hypothesis, you now know the cause — proceed to fix.
- If it doesn't, the hypothesis was wrong. That's a real result, not a failure: return to step 3 with the new information the instrumentation gave you. Don't discard what you just learned by jumping to an unrelated guess.

### 5. Fix

Fix the cause identified in step 4, not the symptom observed in step 1. A fix that makes the minimized repro pass without addressing the confirmed cause is a patch, not a fix — it will resurface in a different shape.

- Keep the fix scoped to the diagnosed cause. Don't bundle in unrelated cleanup while you're in the area — that's a separate change (see the `developer-tdd` skill for keeping changes small generally).

### 6. Regression-test

Add a test that captures the original failure and would catch it again if reintroduced. Run it against the pre-fix code first if practical (revert the fix, confirm the test fails, reapply) — this proves the test actually exercises the bug rather than passing regardless.

- The minimized repro from step 2 is usually most of this test already.
- Skipping this step means the next person (including future you) rediscovers the same bug the hard way.

## Working the Loop

- Don't skip from "reproduce" straight to "fix" on a hunch — a fix applied before the cause is confirmed is a guess wearing a fix's clothes. If it happens to work, you still don't know why, which means you don't know what else it might have broken.
- Time-box hypothesis cycles. If several specific, falsifiable hypotheses in a row have all been wrong, that's a signal the mental model of the system is off somewhere upstream — step back and re-examine assumptions rather than generating a sixth guess from the same wrong model.
- Binary search is a hypothesis-generation strategy, not a replacement for one: "is the bug before or after this point" is itself a falsifiable hypothesis, tested by instrumenting the midpoint.

## Anti-Patterns to Flag

- Changing multiple things at once "to see what fixes it" — when it works, you don't know which change mattered, and the others are now unexplained noise in the diff.
- Fixing the first plausible-looking issue found while reading code, without confirming it's actually the cause of *this* failure.
- Debugging in the full, unminimized environment when a minimal repro was achievable — every iteration of the loop costs more than it needs to.
- Shipping a fix with no regression test because "it's fixed now" — the next regression has no tripwire.
