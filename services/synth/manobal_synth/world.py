from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

import numpy as np
import polars as pl

from .org import (
    GENDERS,
    HOME_REGIONS,
    LANGUAGES,
    RANK_BANDS,
    TENURE_BANDS,
    UnitSpec,
    battalion_paths,
    build_units,
    company_paths,
    sector_paths,
)
from .personas import PERSONAS, PLAYBOOKS

DEMO_DATE = date(2026, 9, 16)
SIM_NOW = datetime(2026, 9, 16, 4, 30, tzinfo=UTC)
SAMPLE_SIZE = 500
NOTICE_HASH = sha256(b"manobal-privacy-notice-v1").hexdigest()

SHIFTED = {
    "shock": 1.4,
    "buddy": 0.7,
    "night": 1.3,
    "leave_delay": 1.35,
    "missingness": 1.25,
    "noise": 1.2,
}


def _provisional_token(service_no: str) -> str:
    digest = sha256(f"synth:{service_no}".encode()).digest()
    alphabet = "abcdefghijklmnopqrstuvwxyz234567"
    chars = "".join(alphabet[b % 32] for b in digest[:16])
    return f"st_{chars}"


def _rank_for_index(index: int, company_size: int, rng: np.random.Generator) -> str:
    del company_size, rng
    cumulative = 0.0
    pick = (index * 0.6180339887) % 1.0
    for name, share in RANK_BANDS:
        cumulative += share
        if pick <= cumulative:
            return name
    return RANK_BANDS[-1][0]


@dataclass
class World:
    name: str
    seed: int
    personnel: int
    days: int
    demo_date: date
    dates: list[date]
    units: tuple[UnitSpec, ...]
    subjects: pl.DataFrame
    duty: pl.DataFrame
    leave_event: pl.DataFrame
    leave_balance: pl.DataFrame
    org_event: pl.DataFrame
    deployment_event: pl.DataFrame
    incident: pl.DataFrame
    ema: pl.DataFrame
    instrument: pl.DataFrame
    bio_day: pl.DataFrame
    voice_features: pl.DataFrame
    engagement_day: pl.DataFrame
    climate_pulse: pl.DataFrame
    grievance: pl.DataFrame
    buddy_pair: pl.DataFrame
    consent_ledger: pl.DataFrame
    fairness: pl.DataFrame
    ground_truth: pl.DataFrame
    sample_tokens: tuple[str, ...]
    officers: pl.DataFrame
    meta: dict[str, object] = field(default_factory=dict)

    def persist_plan(self) -> dict[str, int]:
        weekly_until = min(420, self.days)
        daily_from = min(421, self.days + 1)
        sample_n = len(self.sample_tokens)
        weekly_days = (weekly_until + 6) // 7
        daily_days = max(0, self.days - 420)
        return {
            "duty_day": self.duty.height,
            "ema": self.ema.height,
            "bio_day": self.bio_day.height,
            "voice_features": self.voice_features.height,
            "indicator_people": sample_n,
            "domain_score_rows": sample_n * 7 * (weekly_days + daily_days),
            "weekly_until": weekly_until,
            "daily_from": daily_from,
        }


def generate_world(
    *,
    world: str = "primary",
    personnel: int = 7200,
    days: int = 540,
    seed: int = 20260916,
) -> World:
    if world not in {"primary", "shifted"}:
        raise ValueError("world must be primary or shifted")
    if personnel < len(PERSONAS):
        raise ValueError("personnel must cover the eight personas")
    rng = np.random.default_rng(seed + (7 if world == "shifted" else 0))
    coeff = SHIFTED if world == "shifted" else {
        "shock": 1.0,
        "buddy": 1.0,
        "night": 1.0,
        "leave_delay": 1.0,
        "missingness": 1.0,
        "noise": 1.0,
    }
    units = build_units()
    companies = company_paths()
    dates = [DEMO_DATE - timedelta(days=days - 1 - offset) for offset in range(days)]
    d0 = days - 1
    subjects = _subjects(personnel, companies, rng)
    n = subjects.height
    tokens = subjects["token"].to_list()

    # 1. Deployment calendar per company
    intensity = np.zeros((len(companies), days), dtype=np.float32)
    night_pressure = np.zeros((len(companies), days), dtype=np.float32)
    hard_area = np.zeros((len(companies), days), dtype=np.float32)
    operation = np.zeros((len(companies), days), dtype=bool)
    for c_idx, path in enumerate(companies):
        theatre = path.split(".")[1]
        base = {"north": 0.55, "central": 0.62, "east": 0.5, "capital": 0.35}[theatre]
        wave = 0.15 * np.sin(np.linspace(0, 8 * np.pi, days) + c_idx)
        intensity[c_idx] = np.clip(base + wave, 0.15, 0.95)
        if theatre == "north":
            hard_area[c_idx] = 1.0
        elif theatre == "central":
            hard_area[c_idx, ::3] = 1.0
        op_start = 90 + (c_idx * 17) % max(days - 40, 1)
        op_end = min(days, op_start + 18)
        operation[c_idx, op_start:op_end] = True
        intensity[c_idx, op_start:op_end] += 0.2
        night_pressure[c_idx] = 0.18 + 0.12 * intensity[c_idx]
        night_pressure[c_idx] *= coeff["night"]

    company_index = {path: i for i, path in enumerate(companies)}
    unit_idx = np.array([company_index[path] for path in subjects["unit_path"].to_list()])

    deployments: list[dict[str, object]] = []
    for c_idx, path in enumerate(companies):
        starts = np.where(np.diff(operation[c_idx].astype(np.int8), prepend=0) == 1)[0]
        ends = np.where(np.diff(operation[c_idx].astype(np.int8), append=0) == -1)[0]
        for start, end in zip(starts, ends, strict=False):
            deployments.append(
                {
                    "id": _uuid(f"dep:{world}:{path}:{int(start)}"),
                    "unit_path": path,
                    "type": "operation_start",
                    "at": _sim_at(dates[int(start)]),
                    "sim_at": _sim_at(dates[int(start)]),
                }
            )
            deployments.append(
                {
                    "id": _uuid(f"dep:{world}:{path}:end:{int(end)}"),
                    "unit_path": path,
                    "type": "operation_end",
                    "at": _sim_at(dates[int(end)]),
                    "sim_at": _sim_at(dates[int(end)]),
                }
            )

    # 2. Roster (vectorised)
    cadence = np.where(subjects["rank_band"].to_numpy() == "gazetted", 7, 6).astype(np.int16)
    day_grid = np.arange(days, dtype=np.int16)[None, :]
    person_grid = np.arange(n, dtype=np.int16)[:, None]
    load = intensity[unit_idx]
    scheduled_rest = (day_grid % cadence[:, None]) == (person_grid % cadence[:, None])
    deny_draw = rng.random((n, days)) < np.minimum(0.55, load)
    rest_denied = scheduled_rest & (load > 0.72) & deny_draw
    rest_day = scheduled_rest & ~rest_denied
    hours = np.clip(
        8.0 + 6.0 * load + rng.normal(0, 0.4 * coeff["noise"], size=(n, days)),
        6.0,
        16.0,
    ).astype(np.float32)
    hours = np.where(rest_day, 0.0, hours)
    night = (~rest_day) & (rng.random((n, days)) < night_pressure[unit_idx])
    hours = np.where(night, np.clip(hours + 1.5, 6.0, 16.0), hours)
    shift_hour = np.where(night, 20, 6).astype(np.int16)

    # 4-6. Life events, latent, leave (after intensity; leave uses family draws)
    family_sep = rng.integers(0, 120, size=n).astype(np.int32)
    home_region = subjects["home_region"].to_list()
    life_rate = {
        "north_band": 0.0009,
        "west_band": 0.0007,
        "east_band": 0.0011,
        "south_band": 0.0008,
    }
    latent = np.zeros((n, days), dtype=np.float32)
    leave_rows: list[dict[str, object]] = []
    org_rows: list[dict[str, object]] = []
    grievance_rows: list[dict[str, object]] = []
    distress = rng.random(n) < 0.06
    onset = np.full(n, -1, dtype=np.int32)
    distress_i = np.where(distress)[0]
    if distress_i.size:
        drawn = np.clip(
            (rng.weibull(1.6, size=distress_i.size) * days * 0.45).astype(np.int32),
            40,
            max(40, days - 20),
        )
        onset[distress_i] = drawn
    family_sep = family_sep + np.array(
        [40 if region == "east_band" else 0 for region in home_region],
        dtype=np.int32,
    )
    work = hours / 12.0 + 0.25 * night + 0.2 * rest_denied
    hard = 0.15 * hard_area[unit_idx]
    recover = np.where(rest_day, 0.08, 0.02)
    rates = np.array([life_rate[region] * coeff["shock"] for region in home_region])
    life_hits = rng.random((n, days)) < rates[:, None]
    swap_hits = operation[unit_idx] & (rng.random((n, days)) < 0.01)
    leave_roll = rng.random((n, days)) < (0.004 / coeff["leave_delay"])
    unit_paths = subjects["unit_path"].to_list()
    hit_i, hit_d = np.where(life_hits)
    if hit_i.size:
        kinds = rng.choice(
            np.array(["illness", "marriage", "childbirth", "land", "finance"]),
            size=hit_i.size,
        )
        for i, d, kind in zip(hit_i.tolist(), hit_d.tolist(), kinds.tolist(), strict=True):
            if kind in {"illness", "marriage", "childbirth"}:
                start = dates[d]
                end = start + timedelta(days=2 if kind == "illness" else 5)
                leave_rows.append(
                    _leave_row(
                        tokens[i],
                        "emergency" if kind == "illness" else "EL",
                        start,
                        end,
                        "approved",
                        kind,
                    )
                )
            elif kind == "land":
                grievance_rows.append(
                    _grievance_row(tokens[i], unit_paths[i], "land_property", dates[d])
                )
                org_rows.append(_org_row(tokens[i], "grievance", dates[d], {"kind": "land"}))
            else:
                org_rows.append(_org_row(tokens[i], "grievance", dates[d], {"kind": "finance"}))
    swap_i, swap_d = np.where(swap_hits)
    for i, d in zip(swap_i.tolist(), swap_d.tolist(), strict=True):
        org_rows.append(_org_row(tokens[i], "duty_swap", dates[d], {"op": True}))
    life_bump = life_hits.astype(np.float32) * 0.28
    stress = np.full(n, 0.12, dtype=np.float32)
    stress = stress + 0.05 * (subjects["tenure_band"].to_numpy() == "0_to_5")
    for d in range(days):
        extra = np.where((distress) & (onset >= 0) & (onset <= d), 0.15, 0.0).astype(np.float32)
        stress = np.clip(
            stress + 0.18 * work[:, d] + hard[:, d] - recover[:, d] + life_bump[:, d] + extra,
            0.0,
            1.0,
        )
        latent[:, d] = stress
    leave_i, leave_d = np.where(leave_roll & (~operation[unit_idx]))
    for i, d in zip(leave_i.tolist(), leave_d.tolist(), strict=True):
        if d < 90:
            continue
        status = "rejected" if load[i, d] > 0.7 and rng.random() < 0.35 else "approved"
        span = int(rng.integers(3, 10))
        end = dates[d] + timedelta(days=span)
        leave_rows.append(_leave_row(tokens[i], "EL", dates[d], end, status, "el_cycle"))
        if status == "approved":
            stop = min(days, d + span + 1)
            rest_day[i, d:stop] = True
            hours[i, d:stop] = 0
            night[i, d:stop] = False

    gaming = rng.random(n) < 0.02
    enrolled = rng.random(n) < 0.42
    wearable = enrolled & (rng.random(n) < 0.35)
    voice_on = enrolled & (rng.random(n) < 0.25)
    companion = enrolled & (rng.random(n) < 0.60)

    # 12. Critical incidents ~12 / year
    incident_rows: list[dict[str, object]] = []
    years = max(days / 365.0, 0.2)
    n_incidents = max(1, int(round(12 * years)))
    for k in range(n_incidents):
        c_idx = int(rng.integers(0, len(companies)))
        d = int(rng.integers(20, days - 5))
        itype = str(rng.choice(["encounter", "ied", "casualty", "accident", "disaster"]))
        incident_rows.append(
            {
                "id": _uuid(f"inc:{world}:{k}"),
                "unit_path": companies[c_idx],
                "type": itype,
                "occurred_at": _sim_at(dates[d]),
                "severity": int(rng.integers(2, 6)),
                "sim_at": _sim_at(dates[d]),
            }
        )
        members = np.where(unit_idx == c_idx)[0]
        bump = rng.uniform(0.08, 0.22, size=members.size).astype(np.float32)
        latent[members, d : min(days, d + 14)] += bump[:, None]

    # 13. Acute 0.4% (not Deepak; Deepak is Director/SOS at D0)
    acute_n = max(1, int(round(0.004 * n)))
    acute_idx = rng.choice(n, size=min(acute_n, n), replace=False)
    acute_date = np.full(n, -1, dtype=np.int32)
    for i in acute_idx:
        if rng.random() < 0.8:
            acute_date[i] = int(np.clip(onset[i] + int(rng.integers(8, 30)), 30, days - 1))
        else:
            acute_date[i] = int(rng.integers(40, days - 1))

    _apply_persona_overlays(
        subjects,
        tokens,
        dates,
        d0,
        hours,
        night,
        rest_day,
        rest_denied,
        shift_hour,
        latent,
        family_sep,
        enrolled,
        wearable,
        voice_on,
        companion,
        leave_rows,
        org_rows,
        grievance_rows,
        incident_rows,
        onset,
        acute_date,
        gaming,
        rng,
    )

    sample_tokens = _sample_tokens(tokens, rng)
    sample_set = set(sample_tokens)

    duty = _duty_frame(tokens, dates, hours, night, rest_day, rest_denied, shift_hour)
    ema, engagement, instruments = _self_report(
        subjects,
        dates,
        latent,
        enrolled,
        gaming,
        coeff,
        rng,
        sample_set,
    )
    bio = _wearables(tokens, dates, hours, night, latent, wearable, sample_set, rng)
    voice = _voice_rows(tokens, dates, latent, voice_on, sample_set, subjects, rng)
    climate = _climate(companies, dates, intensity, rng)
    buddies = _buddies(subjects, enrolled, rng)
    consents = _consents(subjects, enrolled, wearable, voice_on, companion)
    fairness = subjects.select(
        ["token", "gender", "home_region", "language", "sector"]
    )
    ground = pl.DataFrame(
        {
            "token": tokens,
            "world": [world] * n,
            "distress_onset": [
                dates[int(o)] if o >= 0 else None for o in onset.tolist()
            ],
            "acute_date": [
                dates[int(a)] if a >= 0 else None for a in acute_date.tolist()
            ],
            "cohort": [
                "distress" if flag else "typical" for flag in distress.tolist()
            ],
        }
    )
    leave_balance = pl.DataFrame(
        {
            "token": tokens,
            "as_of": [DEMO_DATE] * n,
            "el_days": np.clip(30 - rng.integers(0, 18, size=n), 0, 30).tolist(),
            "cl_days": np.clip(8 - rng.integers(0, 6, size=n), 0, 8).tolist(),
            "other": [{}] * n,
            "sim_at": [_sim_at(DEMO_DATE)] * n,
        }
    )
    officers = _officers()
    subjects = subjects.with_columns(
        pl.Series("enrolled", enrolled.tolist()),
        pl.Series("device_tier", np.where(wearable, "B", "A").tolist()),
        pl.Series("family_separation_days", family_sep.tolist()),
        pl.Series("wearable", wearable.tolist()),
        pl.Series("voice_on", voice_on.tolist()),
        pl.Series("companion", companion.tolist()),
    )
    meta = {
        "world": world,
        "personnel": personnel,
        "days": days,
        "seed": seed,
        "companies": len(companies),
        "causal_order": [
            "deployment",
            "roster",
            "leave",
            "life_events",
            "org_events",
            "latent",
            "sleep_hrv",
            "ema",
            "instruments",
            "voice",
            "climate",
            "incidents",
            "acute",
            "gaming",
            "ground_truth",
        ],
        "synthetic": True,
    }
    return World(
        name=world,
        seed=seed,
        personnel=personnel,
        days=days,
        demo_date=DEMO_DATE,
        dates=dates,
        units=units,
        subjects=subjects,
        duty=duty,
        # The id hashes (token, start, kind, status), so a life event and a scheduled
        # leave that share all four collide on the primary key. Keep the first.
        leave_event=(
            pl.DataFrame(leave_rows).unique(subset=["id"], keep="first", maintain_order=True)
            if leave_rows
            else _empty_leave()
        ),
        leave_balance=leave_balance,
        org_event=pl.DataFrame(org_rows) if org_rows else _empty_org(),
        deployment_event=pl.DataFrame(deployments) if deployments else _empty_deployment(),
        incident=pl.DataFrame(incident_rows) if incident_rows else _empty_incident(),
        ema=ema,
        instrument=instruments,
        bio_day=bio,
        voice_features=voice,
        engagement_day=engagement,
        climate_pulse=climate,
        grievance=pl.DataFrame(grievance_rows) if grievance_rows else _empty_grievance(),
        buddy_pair=buddies,
        consent_ledger=consents,
        fairness=fairness,
        ground_truth=ground,
        sample_tokens=sample_tokens,
        officers=officers,
        meta=meta,
    )


def _subjects(
    personnel: int,
    companies: tuple[str, ...],
    rng: np.random.Generator,
) -> pl.DataFrame:
    n = personnel
    counts = np.full(len(companies), n // len(companies), dtype=np.int32)
    counts[: n % len(companies)] += 1
    persona_company = {persona.id: persona.unit_path for persona in PERSONAS}
    rows: list[dict[str, object]] = []
    used: dict[str, int] = {path: 0 for path in companies}
    for persona in PERSONAS:
        play = PLAYBOOKS[persona.id]
        rows.append(
            {
                "subject_index": len(rows),
                "service_no": persona.service_no,
                "token": persona.token,
                "persona_id": persona.id,
                "unit_path": persona.unit_path,
                "rank_band": persona.rank_band,
                "tenure_band": persona.tenure_band,
                "lifecycle_state": play.lifecycle_state,
                "lifecycle_since": SIM_NOW
                - timedelta(days=35 if persona.id == "karthik" else 180),
                "gender": persona.gender,
                "home_region": persona.home_region,
                "language": persona.language,
                "sector": persona.sector,
                "case_id": persona.case_id,
                "display_label": f"{persona.display_label} Synthetic",
            }
        )
        used[persona.unit_path] += 1
    index = len(PERSONAS)
    for c_idx, path in enumerate(companies):
        sector = path.split(".")[1]
        need = int(counts[c_idx]) - used[path]
        for local in range(max(0, need)):
            service_no = f"SYN-{10000 + index:05d}"
            rows.append(
                {
                    "subject_index": index,
                    "service_no": service_no,
                    "token": _provisional_token(service_no),
                    "persona_id": None,
                    "unit_path": path,
                    "rank_band": _rank_for_index(local, int(counts[c_idx]), rng),
                    "tenure_band": TENURE_BANDS[index % len(TENURE_BANDS)],
                    "lifecycle_state": "inducted",
                    "lifecycle_since": SIM_NOW - timedelta(days=int(rng.integers(60, 400))),
                    "gender": GENDERS[int(rng.random() < 0.12)],
                    "home_region": HOME_REGIONS[index % len(HOME_REGIONS)],
                    "language": LANGUAGES[index % len(LANGUAGES)] if sector != "capital" else "en",
                    "sector": sector,
                    "case_id": None,
                    "display_label": f"Synthetic jawan {index}",
                }
            )
            index += 1
            if index >= n:
                break
        if index >= n:
            break
    while len(rows) < n:
        path = companies[len(rows) % len(companies)]
        service_no = f"SYN-{10000 + len(rows):05d}"
        rows.append(
            {
                "subject_index": len(rows),
                "service_no": service_no,
                "token": _provisional_token(service_no),
                "persona_id": None,
                "unit_path": path,
                "rank_band": "Constable/GD",
                "tenure_band": "0_to_5",
                "lifecycle_state": "inducted",
                "lifecycle_since": SIM_NOW - timedelta(days=120),
                "gender": "male",
                "home_region": "north_band",
                "language": "hi",
                "sector": path.split(".")[1],
                "case_id": None,
                "display_label": f"Synthetic jawan {len(rows)}",
            }
        )
    del persona_company
    return pl.DataFrame(rows[:n])


def _apply_persona_overlays(
    subjects: pl.DataFrame,
    tokens: list[str],
    dates: list[date],
    d0: int,
    hours: np.ndarray,
    night: np.ndarray,
    rest_day: np.ndarray,
    rest_denied: np.ndarray,
    shift_hour: np.ndarray,
    latent: np.ndarray,
    family_sep: np.ndarray,
    enrolled: np.ndarray,
    wearable: np.ndarray,
    voice_on: np.ndarray,
    companion: np.ndarray,
    leave_rows: list[dict[str, object]],
    org_rows: list[dict[str, object]],
    grievance_rows: list[dict[str, object]],
    incident_rows: list[dict[str, object]],
    onset: np.ndarray,
    acute_date: np.ndarray,
    gaming: np.ndarray,
    rng: np.random.Generator,
) -> None:
    by_id = {
        str(pid): i
        for i, pid in enumerate(subjects["persona_id"].to_list())
        if pid is not None
    }
    arjun = by_id["arjun"]
    start = d0 - 30
    hours[arjun, : start] = 8.0
    rest_day[arjun, :start:7] = True
    hours[arjun, :start:7] = 0
    night[arjun, :start] = False
    rest_day[arjun, start : start + 19] = False
    rest_denied[arjun, start : start + 4] = True
    hours[arjun, start : start + 19] = 12.5
    night[arjun, start : start + 19] = np.array(
        [d % 2 == 0 for d in range(19)]
    )
    shift_hour[arjun, start : start + 19] = np.where(night[arjun, start : start + 19], 20, 6)
    latent[arjun, : d0 - 45] = 0.18
    latent[arjun, d0 - 45 : d0 - 24] = np.linspace(0.2, 0.45, 21)
    latent[arjun, d0 - 24 : d0 + 1] = np.linspace(0.5, 0.86, 25)[: hours.shape[1] - (d0 - 24)]
    onset[arjun] = d0 - 20
    acute_date[arjun] = min(d0 + 4, hours.shape[1] - 1)
    enrolled[arjun] = True
    wearable[arjun] = True
    voice_on[arjun] = False
    companion[arjun] = True
    gaming[arjun] = False

    meena = by_id["meena"]
    family_sep[meena] = 420
    enrolled[meena] = True
    wearable[meena] = False
    voice_on[meena] = False
    leave_rows.append(
        _leave_row(tokens[meena], "EL", dates[d0 - 40], dates[d0 - 33], "rejected", "ops")
    )
    leave_rows.append(
        _leave_row(tokens[meena], "EL", dates[d0 - 12], dates[d0 - 5], "rejected", "shortfall")
    )
    latent[meena, d0 - 40 :] = np.clip(np.linspace(0.4, 0.72, hours.shape[1] - (d0 - 40)), 0, 1)
    onset[meena] = d0 - 14

    imran = by_id["imran"]
    latent[imran] = 0.16
    latent[imran, d0 - 7 : d0 + 1] = np.linspace(0.22, 0.48, 8)
    hours[imran] = 8.0
    rest_day[imran, ::7] = True
    hours[imran, ::7] = 0
    enrolled[imran] = True
    wearable[imran] = True
    voice_on[imran] = False
    onset[imran] = -1
    acute_date[imran] = -1

    thomas = by_id["thomas"]
    latent[thomas] = 0.12
    hours[thomas] = 8.0
    rest_day[thomas, ::7] = True
    hours[thomas, ::7] = 0
    enrolled[thomas] = True
    wearable[thomas] = False
    voice_on[thomas] = False
    companion[thomas] = False
    onset[thomas] = -1
    acute_date[thomas] = -1

    lalit = by_id["lalit"]
    enrolled[lalit] = True
    wearable[lalit] = False
    incident_rows.append(
        {
            "id": _uuid("inc:lalit:ied"),
            "unit_path": "force.central.c02.bravo",
            "type": "ied",
            "occurred_at": _sim_at(dates[d0 - 3]),
            "severity": 4,
            "sim_at": _sim_at(dates[d0 - 3]),
        }
    )
    latent[lalit, d0 - 3 :] = np.clip(latent[lalit, d0 - 3 :] + 0.2, 0, 1)

    deepak = by_id["deepak"]
    latent[deepak] = 0.2
    enrolled[deepak] = True
    wearable[deepak] = True
    voice_on[deepak] = True
    companion[deepak] = True
    acute_date[deepak] = -1
    onset[deepak] = -1

    rajesh = by_id["rajesh"]
    enrolled[rajesh] = True
    wearable[rajesh] = False
    grievance_rows.append(
        _grievance_row(
            tokens[rajesh],
            "force.central.c03.delta",
            "land_property",
            dates[d0 - 60],
            open_days=60,
        )
    )
    for d in range(d0 - 45, d0 + 1):
        if d % 4 == 0:
            org_rows.append(_org_row(tokens[rajesh], "duty_swap", dates[d], {"rising": True}))
    latent[rajesh, d0 - 30 :] = np.clip(np.linspace(0.35, 0.68, hours.shape[1] - (d0 - 30)), 0, 1)
    onset[rajesh] = d0 - 12
    hours[rajesh] = 8.5
    night[rajesh] = False

    karthik = by_id["karthik"]
    enrolled[karthik] = True
    wearable[karthik] = False
    voice_on[karthik] = True
    leave_start = d0 - 37
    leave_end = d0 - 2
    leave_rows.append(
        _leave_row(
            tokens[karthik],
            "EL",
            dates[leave_start],
            dates[leave_end],
            "approved",
            "bereavement",
        )
    )
    rest_day[karthik, leave_start : leave_end + 1] = True
    hours[karthik, leave_start : leave_end + 1] = 0
    latent[karthik] = 0.22
    latent[karthik, leave_end:] = 0.28
    org_rows.append(
        _org_row(
            tokens[karthik],
            "posting_change",
            dates[leave_end],
            {"reason": "return_from_leave"},
        )
    )
    onset[karthik] = -1
    del rng


def _sample_tokens(tokens: list[str], rng: np.random.Generator) -> tuple[str, ...]:
    personas = [persona.token for persona in PERSONAS]
    pool = [token for token in tokens if token not in set(personas)]
    take = min(SAMPLE_SIZE, len(pool))
    extra = rng.choice(pool, size=take, replace=False).tolist() if take else []
    return tuple(personas + extra)


def _duty_frame(
    tokens: list[str],
    dates: list[date],
    hours: np.ndarray,
    night: np.ndarray,
    rest_day: np.ndarray,
    rest_denied: np.ndarray,
    shift_hour: np.ndarray,
) -> pl.DataFrame:
    n, days = hours.shape
    token_col = np.repeat(np.array(tokens, dtype=object), days)
    date_col = np.tile(np.array(dates, dtype=object), n)
    sim = [_sim_at(d) for d in dates] * n
    return pl.DataFrame(
        {
            "token": token_col.tolist(),
            "date": date_col.tolist(),
            "hours": np.round(hours.ravel(), 2).tolist(),
            "shift_start": [f"{int(h):02d}:00:00" for h in shift_hour.ravel().tolist()],
            "night": night.ravel().tolist(),
            "rest_day": rest_day.ravel().tolist(),
            "rest_denied": rest_denied.ravel().tolist(),
            "sim_at": sim,
        }
    )


def _self_report(
    subjects: pl.DataFrame,
    dates: list[date],
    latent: np.ndarray,
    enrolled: np.ndarray,
    gaming: np.ndarray,
    coeff: dict[str, float],
    rng: np.random.Generator,
    sample_set: set[str],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    tokens = subjects["token"].to_list()
    langs = subjects["language"].to_list()
    n, days = latent.shape
    d0 = days - 1
    arjun_token = next(persona.token for persona in PERSONAS if persona.id == "arjun")
    ema_rows: list[dict[str, object]] = []
    eng_rows: list[dict[str, object]] = []
    inst_rows: list[dict[str, object]] = []
    for i in range(n):
        token = tokens[i]
        if token not in sample_set or not enrolled[i]:
            continue
        for d in range(days):
            expected = 1
            miss = min(0.85, 0.12 + 0.5 * float(latent[i, d]) * coeff["missingness"])
            completed = 0 if rng.random() < miss else 1
            if token == arjun_token and d >= d0 - 10:
                completed = 1 if rng.random() < 0.35 else 0
            eng_rows.append(
                {
                    "token": token,
                    "date": dates[d],
                    "expected": expected,
                    "completed": completed,
                    "sim_at": _sim_at(dates[d]),
                }
            )
            if completed:
                mood = int(np.clip(round(5 - 3.2 * latent[i, d] + rng.normal(0, 0.3)), 1, 5))
                energy = int(np.clip(round(5 - 3.0 * latent[i, d] + rng.normal(0, 0.3)), 1, 5))
                sleep_q = int(np.clip(round(5 - 3.4 * latent[i, d] + rng.normal(0, 0.3)), 1, 5))
                sleep_h = float(np.clip(6.8 - 2.4 * latent[i, d] + rng.normal(0, 0.2), 3.5, 8.5))
                if gaming[i]:
                    mood, energy, sleep_q = 4, 4, 4
                ema_rows.append(
                    {
                        "id": _uuid(f"ema:{token}:{dates[d]}"),
                        "token": token,
                        "at": _sim_at(dates[d]),
                        "mood": mood,
                        "energy": energy,
                        "sleep_quality": sleep_q,
                        "sleep_hours": round(sleep_h, 2),
                        "tags": ["duty"] if latent[i, d] > 0.5 else [],
                        "source": "app",
                        "sim_at": _sim_at(dates[d]),
                    }
                )
            if d % 30 == 0:
                inst_rows.append(
                    _instrument(token, dates[d], "pss10", langs[i], latent[i, d], 10, 4)
                )
                inst_rows.append(
                    _instrument(token, dates[d], "cbi_personal", langs[i], latent[i, d], 6, 4)
                )
            if d % 14 == 0:
                inst_rows.append(
                    _instrument(token, dates[d], "who5", langs[i], 1.0 - latent[i, d], 5, 5)
                )
                inst_rows.append(
                    _instrument(token, dates[d], "phq9", langs[i], latent[i, d], 9, 3)
                )
                inst_rows.append(
                    _instrument(token, dates[d], "gad7", langs[i], latent[i, d], 7, 3)
                )
    ema = pl.DataFrame(ema_rows) if ema_rows else _empty_ema()
    engagement = pl.DataFrame(eng_rows) if eng_rows else _empty_engagement()
    instruments = pl.DataFrame(inst_rows) if inst_rows else _empty_instrument()
    return ema, engagement, instruments


def _instrument(
    token: str,
    on: date,
    kind: str,
    lang: str,
    load: float,
    items: int,
    high: int,
) -> dict[str, object]:
    values = [int(np.clip(round(load * high + 0.2), 0, high)) for _ in range(items)]
    total = float(sum(values))
    if kind == "who5":
        total = float(sum(int(np.clip(round((1.0 - load) * high), 0, high)) for _ in range(items)))
        values = [int(np.clip(round((1.0 - load) * high), 0, high)) for _ in range(items)]
    return {
        "id": _uuid(f"inst:{token}:{kind}:{on}"),
        "token": token,
        "at": _sim_at(on),
        "kind": kind,
        "items": {"q": values},
        "total": total,
        "lang": lang,
        "validated": kind in {"who5", "phq9", "gad7"},
        "visibility": "shared",
        "sim_at": _sim_at(on),
    }


def _wearables(
    tokens: list[str],
    dates: list[date],
    hours: np.ndarray,
    night: np.ndarray,
    latent: np.ndarray,
    wearable: np.ndarray,
    sample_set: set[str],
    rng: np.random.Generator,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    n, days = hours.shape
    d0 = days - 1
    arjun_token = next(p.token for p in PERSONAS if p.id == "arjun")
    for i in range(n):
        if not wearable[i] or tokens[i] not in sample_set:
            continue
        for d in range(days):
            if rng.random() > 0.6:
                continue
            sleep = float(np.clip(410 - 90 * latent[i, d] - 20 * night[i, d], 220, 480))
            if tokens[i] == arjun_token:
                t = (d - (d0 - 45)) / 45 if d >= d0 - 45 else 0.0
                sleep = float(np.clip(6.5 * 60 - t * (6.5 - 4.2) * 60, 240, 420))
            rows.append(
                {
                    "token": tokens[i],
                    "date": dates[d],
                    "sleep_min": int(sleep),
                    "sleep_eff": round(float(np.clip(92 - 18 * latent[i, d], 70, 96)), 2),
                    "rhr": round(float(58 + 14 * latent[i, d] + rng.normal(0, 1)), 2),
                    "hrv_rmssd": round(float(48 - 18 * latent[i, d] + rng.normal(0, 2)), 2),
                    "steps": int(
                        np.clip(8500 - 2000 * latent[i, d] + hours[i, d] * 80, 1200, 16000)
                    ),
                    "spo2": 97.0,
                    "wear_minutes": 1200,
                    "sim_at": _sim_at(dates[d]),
                }
            )
    return pl.DataFrame(rows) if rows else _empty_bio()


def _voice_rows(
    tokens: list[str],
    dates: list[date],
    latent: np.ndarray,
    voice_on: np.ndarray,
    sample_set: set[str],
    subjects: pl.DataFrame,
    rng: np.random.Generator,
) -> pl.DataFrame:
    langs = subjects["language"].to_list()
    rows: list[dict[str, object]] = []
    n, days = latent.shape
    for i in range(n):
        if not voice_on[i] or tokens[i] not in sample_set:
            continue
        baseline = rng.normal(0, 1, size=88).astype(np.float32)
        for d in range(days):
            if rng.random() > 0.4:
                continue
            vec = (baseline + 0.08 * float(latent[i, d]) * rng.normal(0, 1, size=88)).tolist()
            rows.append(
                {
                    "id": _uuid(f"voice:{tokens[i]}:{dates[d]}"),
                    "token": tokens[i],
                    "at": _sim_at(dates[d]),
                    "egemaps": [float(v) for v in vec],
                    "duration_s": 12.0,
                    "lang": langs[i],
                    "sim_at": _sim_at(dates[d]),
                }
            )
    return pl.DataFrame(rows) if rows else _empty_voice()


def _climate(
    companies: tuple[str, ...],
    dates: list[date],
    intensity: np.ndarray,
    rng: np.random.Generator,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    weeks = dates[::7]
    for c_idx, path in enumerate(companies):
        for week in weeks:
            d = min(len(dates) - 1, dates.index(week))
            load = float(intensity[c_idx, d])
            n_resp = int(40 + 20 * load)
            low = max(3, int(n_resp * (0.55 - 0.25 * load)))
            mid = max(3, int(n_resp * 0.3))
            high = max(0, n_resp - low - mid)
            for bucket, count in (("low", low), ("mid", mid), ("high", high)):
                if count <= 0:
                    continue
                rows.append(
                    {
                        "id": _uuid(f"pulse:{path}:{week}:{bucket}"),
                        "unit_path": path,
                        "week": week,
                        "question_id": "morale",
                        "response_bucket": bucket,
                        "n": count,
                        "sim_at": _sim_at(week),
                    }
                )
    del rng
    return pl.DataFrame(rows)


def _buddies(
    subjects: pl.DataFrame,
    enrolled: np.ndarray,
    rng: np.random.Generator,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    grouped: dict[str, list[int]] = {}
    for i, path in enumerate(subjects["unit_path"].to_list()):
        grouped.setdefault(path, []).append(i)
    tokens = subjects["token"].to_list()
    for path, members in grouped.items():
        consented = [i for i in members if enrolled[i]]
        rng.shuffle(consented)
        for a, b in zip(consented[0::2], consented[1::2], strict=False):
            token_a, token_b = sorted((tokens[a], tokens[b]))
            rows.append(
                {
                    "id": _uuid(f"buddy:{token_a}:{token_b}"),
                    "token_a": token_a,
                    "token_b": token_b,
                    "unit_path": path,
                    "since": SIM_NOW - timedelta(days=40),
                    "active": True,
                    "sim_at": SIM_NOW - timedelta(days=40),
                }
            )
    return pl.DataFrame(rows) if rows else _empty_buddy()


def _consents(
    subjects: pl.DataFrame,
    enrolled: np.ndarray,
    wearable: np.ndarray,
    voice_on: np.ndarray,
    companion: np.ndarray,
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    tokens = subjects["token"].to_list()
    langs = subjects["language"].to_list()
    personas = {p.id: p.token for p in PERSONAS}
    play_by_token = {personas[pid]: PLAYBOOKS[pid] for pid in personas}
    for i, token in enumerate(tokens):
        play = play_by_token.get(token)
        granted = {"hr_derived"}
        if play is not None:
            granted = set(play.consents)
        else:
            if enrolled[i]:
                granted.add("self_report")
            if wearable[i]:
                granted.add("wearable")
            if voice_on[i]:
                granted.add("voice_features")
            if companion[i]:
                granted.add("ai_conversation")
        for data_type in (
            "hr_derived",
            "self_report",
            "wearable",
            "voice_features",
            "ai_conversation",
            "trend_share",
            "buddy",
            "family_line",
        ):
            action = "grant" if data_type in granted else "withdraw"
            if data_type == "hr_derived":
                action = "grant"
            rows.append(
                {
                    "id": _uuid(f"consent:{token}:{data_type}"),
                    "token": token,
                    "data_type": data_type,
                    "purpose": "welfare_support",
                    "action": action,
                    "text_hash": NOTICE_HASH,
                    "lang": langs[i],
                    "app_version": "0.1.0",
                    "at": SIM_NOW - timedelta(days=10),
                    "sim_at": SIM_NOW - timedelta(days=10),
                }
            )
    return pl.DataFrame(rows)


def _officers() -> pl.DataFrame:
    named = [
        ("uwo-sunita", "Insp. Sunita Rawat Synthetic", "uwo", "force.central.c02"),
        ("counsellor-anjali", "Ms. Anjali Deshmukh Synthetic", "counsellor", "force.central"),
        ("mo-farah", "Dr. Farah Siddiqui Synthetic", "mo", "force.north.n01"),
        ("commander-menon", "Commandant R. K. Menon Synthetic", "commander", "force.central.c02"),
        ("hq-central", "IG Sector Central Synthetic", "hq", "force"),
        ("wdec-kavita", "Dr. Kavita Rao Synthetic", "wdec", "force"),
        ("dpo-synthetic", "DPO Synthetic", "dpo", "force"),
        ("integrator-synthetic", "HRMS custodian Synthetic", "hrms_integrator", "force"),
        ("admin-synthetic", "System admin Synthetic", "admin", "force"),
        ("director-synthetic", "Demo director Synthetic", "director", "force"),
    ]
    rows = [
        {
            "id": _uuid(f"officer:{oid}"),
            "entra_oid": f"demo-{oid}",
            "display_label": label,
            "role": role,
            "unit_path": path,
            "valid_from": SIM_NOW - timedelta(days=30),
            "valid_to": None,
        }
        for oid, label, role, path in named
    ]
    for path in battalion_paths():
        rows.append(
            {
                "id": _uuid(f"officer:uwo:{path}"),
                "entra_oid": f"demo-uwo-{path}",
                "display_label": f"UWO {path} Synthetic",
                "role": "uwo",
                "unit_path": path,
                "valid_from": SIM_NOW - timedelta(days=30),
                "valid_to": None,
            }
        )
        rows.append(
            {
                "id": _uuid(f"officer:mo:{path}"),
                "entra_oid": f"demo-mo-{path}",
                "display_label": f"MO {path} Synthetic",
                "role": "mo",
                "unit_path": path,
                "valid_from": SIM_NOW - timedelta(days=30),
                "valid_to": None,
            }
        )
    for path in sector_paths():
        rows.append(
            {
                "id": _uuid(f"officer:counsellor:{path}"),
                "entra_oid": f"demo-counsellor-{path}",
                "display_label": f"Counsellor {path} Synthetic",
                "role": "counsellor",
                "unit_path": path,
                "valid_from": SIM_NOW - timedelta(days=30),
                "valid_to": None,
            }
        )
    return pl.DataFrame(rows)


def _leave_row(
    token: str,
    kind: str,
    start: date,
    end: date,
    status: str,
    reason: str,
) -> dict[str, object]:
    return {
        "id": _uuid(f"leave:{token}:{start}:{kind}:{status}"),
        "token": token,
        "type": kind,
        "applied_at": _sim_at(start),
        "from_date": start,
        "to_date": end,
        "status": status,
        "reason_code": reason,
        "sim_at": _sim_at(start),
    }


def _org_row(token: str, kind: str, on: date, meta: dict[str, object]) -> dict[str, object]:
    return {
        "id": _uuid(f"org:{token}:{kind}:{on}:{meta}"),
        "token": token,
        "type": kind,
        "at": _sim_at(on),
        "meta": meta,
        "sim_at": _sim_at(on),
    }


def _grievance_row(
    token: str,
    unit_path: str,
    category: str,
    opened: date,
    open_days: int = 14,
) -> dict[str, object]:
    token_hash = sha256(token.encode()).hexdigest()
    return {
        "id": _uuid(f"griev:{token}:{opened}:{category}"),
        "token_hash": token_hash,
        "unit_path": unit_path,
        "category": category,
        "text_enc": None,
        "status": "open",
        "sla_due": _sim_at(opened + timedelta(days=30)),
        "opened_at": _sim_at(opened),
        "closed_at": None,
        "sim_at": _sim_at(opened),
        "open_days": open_days,
        "token": token,
    }


def _sim_at(on: date) -> datetime:
    return datetime(on.year, on.month, on.day, 6, 0, tzinfo=UTC)


def _uuid(value: str) -> str:
    digest = sha256(value.encode()).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def _empty_leave() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token": pl.String,
            "type": pl.String,
            "applied_at": pl.Datetime(time_zone="UTC"),
            "from_date": pl.Date,
            "to_date": pl.Date,
            "status": pl.String,
            "reason_code": pl.String,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_org() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token": pl.String,
            "type": pl.String,
            "at": pl.Datetime(time_zone="UTC"),
            "meta": pl.Object,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_deployment() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "unit_path": pl.String,
            "type": pl.String,
            "at": pl.Datetime(time_zone="UTC"),
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_incident() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "unit_path": pl.String,
            "type": pl.String,
            "occurred_at": pl.Datetime(time_zone="UTC"),
            "severity": pl.Int64,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_ema() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token": pl.String,
            "at": pl.Datetime(time_zone="UTC"),
            "mood": pl.Int64,
            "energy": pl.Int64,
            "sleep_quality": pl.Int64,
            "sleep_hours": pl.Float64,
            "tags": pl.List(pl.String),
            "source": pl.String,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_engagement() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "token": pl.String,
            "date": pl.Date,
            "expected": pl.Int64,
            "completed": pl.Int64,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_instrument() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token": pl.String,
            "at": pl.Datetime(time_zone="UTC"),
            "kind": pl.String,
            "items": pl.Object,
            "total": pl.Float64,
            "lang": pl.String,
            "validated": pl.Boolean,
            "visibility": pl.String,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_bio() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "token": pl.String,
            "date": pl.Date,
            "sleep_min": pl.Int64,
            "sleep_eff": pl.Float64,
            "rhr": pl.Float64,
            "hrv_rmssd": pl.Float64,
            "steps": pl.Int64,
            "spo2": pl.Float64,
            "wear_minutes": pl.Int64,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_voice() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token": pl.String,
            "at": pl.Datetime(time_zone="UTC"),
            "egemaps": pl.List(pl.Float64),
            "duration_s": pl.Float64,
            "lang": pl.String,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )


def _empty_grievance() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token_hash": pl.String,
            "unit_path": pl.String,
            "category": pl.String,
            "text_enc": pl.Null,
            "status": pl.String,
            "sla_due": pl.Datetime(time_zone="UTC"),
            "opened_at": pl.Datetime(time_zone="UTC"),
            "closed_at": pl.Null,
            "sim_at": pl.Datetime(time_zone="UTC"),
            "open_days": pl.Int64,
            "token": pl.String,
        }
    )


def _empty_buddy() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "id": pl.String,
            "token_a": pl.String,
            "token_b": pl.String,
            "unit_path": pl.String,
            "since": pl.Datetime(time_zone="UTC"),
            "active": pl.Boolean,
            "sim_at": pl.Datetime(time_zone="UTC"),
        }
    )
