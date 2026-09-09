"""Celery task wrappers. Logic lives in the modules they call."""

from __future__ import annotations

from manobal_core.celery import app


@app.task(name="manobal_core.tasks.score_all_subjects")  # type: ignore[untyped-decorator]
def score_all_subjects() -> int:
    from manobal_core.scoring.nightly import score_all_subjects as run

    return run()


@app.task(name="manobal_core.tasks.escalate_unacked_t4")  # type: ignore[untyped-decorator]
def escalate_unacked_t4() -> int:
    from manobal_core.alerting.escalate import escalate_unacknowledged

    return len(escalate_unacknowledged())


@app.task(name="manobal_core.tasks.resume_pending_erasures")  # type: ignore[untyped-decorator]
def resume_pending_erasures() -> int:
    from manobal_core.erasure.saga import resume_pending

    return resume_pending()


@app.task(name="manobal_core.tasks.advance_erasure")  # type: ignore[untyped-decorator]
def advance_erasure_task(request_id: int) -> int:
    from manobal_core.apps.governance.models import ErasureRequest
    from manobal_core.erasure.saga import advance_erasure

    request = ErasureRequest.objects.get(pk=request_id)
    done = advance_erasure(request)
    return done.id
