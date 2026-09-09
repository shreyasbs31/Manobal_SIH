"""Physiological signal store — D4 (SDD §5.1).

Intentionally empty for now. ``bio_store`` holds high-frequency wearable
telemetry — resting heart rate, HRV, sleep staging, step counts — which is a
TimescaleDB hypertable in the target deployment, and modelling it against plain
PostgreSQL would mean writing a partitioning scheme now and discarding it later.
The database and its grants already exist; only the tables are deferred.

Nothing downstream is blocked by this. A person whose wearable data is absent is
handled by coverage renormalisation in the risk engine (§4.4) in exactly the same
way as a person who declined the device: D4 is simply not among the domains
present, the remaining domain weights are renormalised over what *is* available,
and the corroboration gate still requires two domains to raise a tier above T1.

Adding the tables later is additive — a migration in this app and a domain
appearing in assessments — and requires no change to the engine, whose contract
is over whichever domains it is handed.
"""

from __future__ import annotations
