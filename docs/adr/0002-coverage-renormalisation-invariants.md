# ADR 0002 — What coverage renormalisation actually guarantees

- **Status**: Accepted, with an open design question in §4 requiring a decision
- **Date**: 2026-09-10
- **Relates to**: SDD §4.5 step 4, FR-3.3, §7.7, §9.1, §12.3 P2, KPI K8/K10

## 1. Context

SDD §4.5 defines the composite as a coverage-renormalised weighted mean:

```
WSI = sum_{d in A} w_d * Z_d / sum_{d in A} w_d      A = {d : coverage_d >= 0.6}
```

and states the intent plainly: *"A person who declines wearables must not score
lower for it, and a person who opts in must not be penalised for having more
data. Without renormalisation, opting in becomes materially risky and the
voluntary model collapses."*

SDD §9.1 then specifies a property test:

```python
def test_opting_out_never_changes_tier(history, ruleset):
    full = score(history, ruleset)
    reduced = score(history.without_domain("D4"), ruleset)
    assert reduced.tier == full.tier or reduced.insufficient_coverage
```

## 2. The problem with the invariant as written

It cannot hold, for any weighted mean, for reasons that are arithmetic rather
than architectural. Removing a domain whose score is above the current mean
lowers the mean; removing one below it raises the mean. The tier is a threshold
function of the mean, so it moves.

An invariant that cannot hold has one of two fates: it is deleted, or it is
weakened until it passes and stops meaning anything. Writing
`assert reduced.tier == full.tier or True` would satisfy CI and protect nobody.

## 3. What we assert instead

Three properties, all mechanically verified in
`packages/manobal-risk/tests/test_properties.py`:

1. **The composite does not depend on breadth of participation.**
   `test_wsi_does_not_depend_on_how_many_domains_a_person_shares` — two subjects
   carrying identical adversity get an identical WSI whether they contribute two
   domains or seven. This is the property §4.5's prose is describing, and it is
   the one that matters for fairness between people.

2. **Equal adversity yields an equal tier once the gate is satisfiable.**
   `test_equal_adversity_yields_an_equal_tier_once_both_can_corroborate`.

3. **Withdrawal cannot create corroboration.**
   `test_an_uncorroborated_person_cannot_become_visible_by_withdrawing_data` —
   removing data can only shrink the set of breaching domains, so a subject who
   fails the corroboration gate still fails it afterwards and remains capped at
   T1, which no officer ever sees.

## 4. Open design question — withdrawal dilution

Property 3 is deliberately narrower than "withdrawal cannot expose you", because
the wider claim is false. A worked counterexample, asserted as a characterisation
test in `tests/test_withdrawal_dilution.py`:

A subject with `D1_workload = 0.9`, `D2_leave = 0.9`, `D4_physiological = 0.0`
and `D5_self_report = 0.0` has two breaching domains, so the corroboration gate
is satisfied — but the two calm domains pull the mean to **0.407**, below the T2
boundary. The subject sits at **T1: private, nobody is told.**

The same subject withdraws wearable and self-report consent. Nothing about their
behaviour changed. The mean is now **0.9**. They are **T3: immediate push to the
welfare officer.**

This directly contradicts SDD §7.7's promise of *"withdrawal without friction —
one screen, no justification, no notification to anyone, immediate effect"*. It
is not frictionless if it is a gamble, and the first person it happens to will
tell their unit that turning off the wearable got them reported. That is exactly
the trust collapse K10 measures and §12.3 P2 warns about.

### Options

| # | Option | Cost |
|---|---|---|
| A | Accept, and disclose it in the withdrawal consent text | Free to build; makes the withdrawal screen frightening, which suppresses withdrawal — a different §7.7 failure |
| B | Suppress any tier *increase* attributable solely to reduced coverage, for a settling period after a withdrawal event | Service-layer work in `manobal-core`; the engine is stateless and cannot see withdrawal events. Preserves both promises |
| C | Replace the mean with a coverage-renormalised high quantile or max-of-domains, so a benign domain never dilutes an adverse one | Recalibrates every threshold in the ruleset; changes the meaning of the weights |

**Recommendation: B**, with the ruleset unchanged. It keeps the §4.5 formula, keeps
the fairness property of §3, and makes the §7.7 promise true. Implemented as a
`WithdrawalSettlingPolicy` in the core scoring orchestrator, it is auditable and
removable without touching the safety-critical engine.

**This decision is not yet made.** Until it is, the characterisation tests pin the
current behaviour so a future change to it is deliberate.

## 5. Consequences

The engine ships with the §4.5 formula exactly as specified. The §9.1 invariant is
replaced by three provable ones, and the gap between them is documented here
rather than closed by a vacuous assertion.
