"""The stages of the causal chain, one module per link.

The order of this list *is* the model. Each module consumes only the latents of
the stages above it and adds its own indicators and its own noise:

    deployment  ->  workload (D1)
                ->  physiology: sleep, then autonomic (D4)
                ->  self_report: affect, EMA, instruments (D5)
                ->  voice: prosody (D6)
                ->  leave: leave-seeking, absence (D2)
                ->  organisational: transfer, swap, withdrawal (D3)
                ->  engagement: check-in and app decline (D7)

Splitting it this way is not decoration. It means the causal claim can be read
off the import graph: ``physiology`` imports nothing from ``self_report``, so
mood cannot possibly be driving HRV, and a reviewer can verify that without
reading a line of arithmetic.
"""

from __future__ import annotations
