from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings


class ClockState(BaseModel):
    sim_now: datetime
    speed: float
    running: bool
    wall_time_compression: float


class ClockUpdate(BaseModel):
    sim_now: datetime | None = None
    speed: float | None = Field(default=None, ge=0, le=10000)
    running: bool | None = None
    advance_seconds: float = Field(default=0, ge=0, le=31_536_000)


def wall_seconds_for_sla(
    simulated_seconds: float,
    settings: Settings | None = None,
) -> float:
    active_settings = settings or get_settings()
    return simulated_seconds / active_settings.sim_time_compression


async def get_clock(
    session: AsyncSession,
    settings: Settings | None = None,
    *,
    for_update: bool = False,
) -> ClockState:
    suffix = " FOR UPDATE" if for_update else ""
    row = (
        (
            await session.execute(
                text(
                    """
                SELECT
                    sim_now,
                    speed,
                    running,
                    updated_at
                FROM sim_clock
                WHERE id = 1
                """
                    + suffix
                )
            )
        )
        .mappings()
        .one()
    )
    sim_now = row["sim_now"]
    if row["running"]:
        wall_elapsed = datetime.now(UTC) - row["updated_at"]
        sim_now = sim_now + timedelta(seconds=wall_elapsed.total_seconds() * float(row["speed"]))
    return ClockState(
        sim_now=sim_now,
        speed=float(row["speed"]),
        running=bool(row["running"]),
        wall_time_compression=(settings or get_settings()).sim_time_compression,
    )


async def update_clock(
    session: AsyncSession,
    update: ClockUpdate,
    settings: Settings | None = None,
) -> ClockState:
    current = await get_clock(session, settings, for_update=True)
    next_sim_now = (update.sim_now or current.sim_now) + timedelta(seconds=update.advance_seconds)
    next_speed = update.speed if update.speed is not None else current.speed
    next_running = update.running if update.running is not None else current.running
    await session.execute(
        text(
            """
            UPDATE sim_clock
               SET sim_now = :sim_now,
                   speed = :speed,
                   running = :running,
                   updated_at = clock_timestamp()
             WHERE id = 1
            """
        ),
        {
            "sim_now": next_sim_now,
            "speed": next_speed,
            "running": next_running,
        },
    )
    await session.commit()
    return ClockState(
        sim_now=next_sim_now,
        speed=next_speed,
        running=next_running,
        wall_time_compression=(settings or get_settings()).sim_time_compression,
    )
