# ADR 0003 — The personal baseline cannot see a decline that has finished

- **Status**: Accepted. Records a limitation of the design, not a defect to fix in code.
- **Date**: 2026-09-10
- **Relates to**: SDD §4.2, §4.3, §9.1, KPI K4 (false-negative rate), Appendix A.3

## 1. Context

Building the synthetic generator surfaced a property of the scoring design that
the SDD does not state and that would otherwise be discovered as an apparent bug
during validation. It is worth recording plainly, because the first person to
compare flag rates against injected ground truth will conclude the engine is
broken, and they will be wrong.

Scoring an 18-month synthetic cohort through the real ruleset produces:

| Ground-truth group | n | T1 or above | Mean WSI |
|---|---|---|---|
| distress, still declining at window close | 31 | 45.2% | 0.353 |
| distress, decline completed before window close | 28 | **0%** | 0.126 |
| gaming, still declining | 9 | 11.1% | 0.229 |
| gaming, completed | 13 | 0% | 0.121 |
| stable | 139 | 0% | 0.119 |

The middle rows are the finding. Twenty-eight people carrying genuine, injected
distress score a mean WSI of 0.126 — statistically indistinguishable from the
139 stable subjects at 0.119 — and not one of them reaches even T1.

## 2. Why this happens

It is arithmetic, not a tuning failure.

SDD §4.2 scores a person against *their own* trailing 90-day median and MAD.
That choice is the ethical core of the system: it is what stops the platform
penalising someone for sleeping less than their peers, and what makes the
comparison fair across wildly different postings and constitutions.

But a baseline computed over a trailing window is not a fixed reference. It
follows the person. Someone whose sleep degraded over four months and then
stabilised at the degraded level has, by month six, a *new* personal median that
sits at the degraded value. Their deviation score against it is near zero. The
engine is working exactly as specified and reports, correctly, that this person
is not currently deviating from their own norm.

The distinction the engine actually draws is not *distressed* versus *well*. It
is **changing** versus **steady**. Those coincide often enough to be useful, and
they are not the same thing.

## 3. Why we are not "fixing" it

Three candidate fixes were considered and all are worse than the limitation.

**Lengthening the baseline window.** Pushing the window to 12 months would catch
declines up to a year old, at the cost of making the baseline unresponsive to
legitimate change — a transfer to a calmer posting would take a year to register
— and of retaining far more personal history than §7.3's retention policy
contemplates. It trades a bounded blind spot for an unbounded one.

**Freezing the baseline at enrolment.** This defeats the purpose. A person's
normal genuinely changes with posting, age and season, and a frozen reference
would flag every such change as deterioration. It also makes the assessment
depend on *when someone happened to enrol*, which is arbitrary and unfair.

**Adding a cohort comparison for people whose own signal is flat.** This is the
one that sounds most reasonable and is the most dangerous. Comparing a person to
their unit reintroduces exactly the mechanism §4.2 exists to prevent, and it
would fall hardest on people who differ from their cohort for reasons that are
not welfare-related at all.

The limitation is a consequence of a correct decision. It should be documented,
measured and covered by a different mechanism — not engineered away by weakening
the thing that makes the scoring defensible.

## 4. Consequences

**K4 must be reported against two populations, not one.** A single
false-negative rate over everyone with injected distress conflates a detection
failure with a case the design cannot address by construction. Validation must
report:

- K4 over subjects still deviating at assessment time — this measures the engine.
- Separately, the count and share of subjects whose decline completed before the
  window — this measures the blind spot's size, not the engine's accuracy.

`manobal-synth` emits `deteriorating_at_end` per subject in `ground_truth.jsonl`
precisely so this split is computable rather than estimated.

**Nobody should read "45% detected" as the engine's sensitivity.** Against the
population the design can see, that number is the meaningful one. Against the
population it cannot, no threshold change will help.

**The gap needs a non-scoring answer.** People in a settled low state are real
and are arguably in more need than someone with a transient dip. Reaching them
is a job for the routes that do not depend on deviation at all: self-referral,
the acute path, periodic instrument administration read against clinical norms
rather than personal ones, and an officer noticing something. This ADR does not
propose which, but it does assert that the scoring engine is the wrong place to
solve it, and that shipping without acknowledging the gap would misrepresent
what the system does.

**The synthetic corpus deliberately reproduces the gap.** The generator was not
tuned until every injected case became detectable. Ramp durations follow the
SDD's own description of months-long declines, so roughly half the injected
cohort has plateaued by the time an 18-month window closes. A generator tuned to
make the engine look good would have hidden precisely the finding this ADR
records.

## 5. Open question for the clinical reviewers

Is a settled-low state something MANOBAL should attempt to surface at all, given
that doing so requires comparing a person against something other than
themselves? A defensible answer is no — that this is what periodic clinical
screening is for, and the platform should not stretch beyond deviation
detection. That answer needs to come from the WDEC and the clinical panel rather
than from engineering, and it should be recorded before the first validation
report is written, so the K4 figure is interpreted the way it was meant to be.
