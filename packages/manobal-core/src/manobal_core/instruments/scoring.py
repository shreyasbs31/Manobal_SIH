"""Score a completed instrument. Item answers do not leave this function."""

from __future__ import annotations

from dataclasses import dataclass

from manobal_core.instruments.catalogue import PSS10, SPECS, InstrumentSpec, spec_for

PSS10_REVERSED: tuple[int, ...] = (3, 4, 6, 7)
STRAIGHT_LINE_SECONDS_PER_ITEM = 2


@dataclass(frozen=True, slots=True)
class ScoredInstrument:
    spec: InstrumentSpec
    total: float
    acute: bool
    acute_item_code: str
    straight_lined: bool


def score_answers(
    code: str,
    answers: list[int],
    *,
    duration_seconds: int | None = None,
) -> ScoredInstrument:
    """Validate ``answers`` and return a total. The list is not retained."""
    spec = spec_for(code)
    if len(answers) != spec.item_count:
        raise ValueError(f"{spec.code} requires {spec.item_count} answers")
    for value in answers:
        if value < spec.min_value or value > spec.max_value:
            raise ValueError(
                f"{spec.code} answers must be {spec.min_value}-{spec.max_value}"
            )
    total = float(_total(spec, answers))
    acute = False
    acute_code = ""
    if spec.acute_item_index is not None and answers[spec.acute_item_index] > 0:
        acute = True
        acute_code = "phq9_item9_positive"
    return ScoredInstrument(
        spec=spec,
        total=total,
        acute=acute,
        acute_item_code=acute_code,
        straight_lined=_straight_lined(spec, duration_seconds),
    )


def _total(spec: InstrumentSpec, answers: list[int]) -> int:
    if spec.code == PSS10:
        return sum(
            (spec.max_value - value) if index in PSS10_REVERSED else value
            for index, value in enumerate(answers)
        )
    return sum(answers)


def _straight_lined(spec: InstrumentSpec, duration_seconds: int | None) -> bool:
    if duration_seconds is None:
        return False
    floor = spec.item_count * STRAIGHT_LINE_SECONDS_PER_ITEM
    return duration_seconds < floor


def known_codes() -> frozenset[str]:
    return frozenset(SPECS)
