from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import TextClause, text

from .auth import Principal, Role, decode_access_token
from .errors import ApiError


class RowPredicate(StrEnum):
    OWN = "own"
    UNIT_SUBTREE = "unit_subtree"
    ASSIGNED = "assigned"
    AGGREGATE_ONLY = "aggregate_only"
    GOVERNANCE = "governance"
    DEMO_CONTROL = "demo_control"
    AUTHENTICATED = "authenticated"


bearer = HTTPBearer(auto_error=False)
Dependency = Callable[
    [HTTPAuthorizationCredentials | None],
    Awaitable[Principal],
]


def ltree_predicate(column: str, predicate: RowPredicate) -> TextClause:
    if not re.fullmatch(r"[a-z_][a-z0-9_.]*", column):
        raise ValueError("Unsafe SQL column")
    if predicate is RowPredicate.OWN:
        return text(f"{column} = :subject_token")
    if predicate in {RowPredicate.UNIT_SUBTREE, RowPredicate.ASSIGNED}:
        return text(f"{column} <@ CAST(:scope_path AS ltree)")
    raise ValueError(f"{predicate.value} does not map to an individual row predicate")


def _enforce_predicate(principal: Principal, predicate: RowPredicate) -> None:
    if predicate is RowPredicate.AUTHENTICATED:
        return
    if predicate is RowPredicate.OWN and principal.subject_token is None:
        raise ApiError(
            "scope_denied",
            "This route is limited to the signed-in person's data",
            hint="Use a personnel session",
            status_code=403,
        )
    if predicate is RowPredicate.UNIT_SUBTREE and principal.role not in {
        Role.UWO,
        Role.MO,
        Role.ADMIN,
    }:
        raise ApiError(
            "scope_denied",
            "This route requires an assigned unit scope",
            hint="Use an assigned officer session",
            status_code=403,
        )
    if predicate is RowPredicate.ASSIGNED and principal.role is not Role.COUNSELLOR:
        raise ApiError(
            "scope_denied",
            "This route requires an assigned counsellor scope",
            hint="Use a counsellor session",
            status_code=403,
        )
    if predicate is RowPredicate.AGGREGATE_ONLY:
        if principal.role not in {Role.COMMANDER, Role.HQ}:
            raise ApiError(
                "scope_denied",
                "This route is limited to aggregate command scopes",
                hint="Use a command or HQ session",
                status_code=403,
            )
        if principal.subject_token is not None:
            raise ApiError(
                "scope_denied",
                "Aggregate sessions cannot carry a subject token",
                hint="Sign in again with the correct role",
                status_code=403,
            )
    if predicate is RowPredicate.GOVERNANCE and principal.role is not Role.WDEC:
        raise ApiError(
            "scope_denied",
            "This route requires a governance scope",
            hint="Use a WDEC session",
            status_code=403,
        )
    if predicate is RowPredicate.DEMO_CONTROL and principal.role is not Role.DIRECTOR:
        raise ApiError(
            "scope_denied",
            "This route requires the demo director scope",
            hint="Use the demo director session",
            status_code=403,
        )


def require(scope: str, predicate: RowPredicate) -> Dependency:
    async def dependency(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(bearer),
        ] = None,
    ) -> Principal:
        if credentials is None:
            raise ApiError(
                "authentication_required",
                "An access token is required",
                hint="Sign in and retry",
                status_code=401,
            )
        principal = decode_access_token(credentials.credentials)
        if scope not in principal.scopes:
            raise ApiError(
                "scope_denied",
                "The session does not have the required scope",
                hint="Use a role assigned to this surface",
                status_code=403,
            )
        _enforce_predicate(principal, predicate)
        return principal

    return dependency
