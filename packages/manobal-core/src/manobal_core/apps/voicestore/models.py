"""Vocal-acoustic signal store — D6 (SDD §5.1).

Intentionally empty for now, pending pgvector.

Worth being precise about what this store would and would not hold, because the
distinction is the whole reason voice is treated separately. It holds *acoustic
features* — pitch variability, speech rate, pause structure, energy — extracted
on the person's own device. It does not hold audio, and on a Tier A device it
does not hold a transcript either: the recording never leaves the phone. Only on
Tier B, and only with the separate ``transcript_edge`` consent, does text reach
the unit server, and then ephemerally.

D6 carries the lowest confidence and the highest corroboration bar in the
ruleset, for good reason. Acoustic markers are sensitive to a head cold, to
ambient noise, to which of several languages someone is speaking, and to
accents under-represented in whatever the feature extractor was tuned on. Left
unchecked that is a fairness problem aimed squarely at people the system is
meant to help, so the ruleset requires voice to be corroborated by another
domain before it can contribute to a tier at all.

Its absence changes nothing structurally; see the note in ``biostore.models``.
"""

from __future__ import annotations
