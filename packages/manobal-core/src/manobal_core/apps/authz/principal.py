"""The authenticated caller, as derived from a verified token (SDD §6.2).

A :class:`Principal` is frozen and carries only claims that were present in a
signature-verified JWT. Nothing downstream may add a role or widen a scope: if a
capability is not in the token, the caller does not have it, and the fix is at
the identity provider rather than in application code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..governance.enums import Role

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class Principal:
    """An authenticated actor.

    ``subject_token`` is populated only for a ``personnel`` principal and is the
    person's own pseudonymous token. An officer principal never carries one:
    officers act *on* subjects, and giving an officer's identity a subject token
    field would invite code that conflates the two.
    """

    actor_id: str
    role: Role
    force_code: str
    unit_code: str = ""
    #: Verified second-factor methods from the token's ``amr`` claim.
    auth_methods: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=frozenset)
    subject_token: str = ""
    #: Retained for audit correlation with the identity provider's session.
    session_id: str = ""

    @property
    def is_personnel(self) -> bool:
        return self.role is Role.PERSONNEL

    @property
    def is_officer(self) -> bool:
        return self.role in {Role.WELFARE_OFFICER, Role.MEDICAL_OFFICER}

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    @classmethod
    def from_claims(
        cls, claims: Mapping[str, Any], *, second_factor_methods: Sequence[str]
    ) -> Principal:
        """Build a principal from verified claims.

        Unknown role strings map to nothing rather than to a default. A token
        naming a role this deployment does not recognise is a configuration
        error at the identity provider, and the safe reading of an unrecognised
        role is "no privileges", never "the least privileged role we happen to
        have".
        """
        raw_role = str(claims.get("manobal_role", "")).strip()
        role = Role(raw_role) if raw_role in Role.values else None
        if role is None:
            msg = f"token carries no recognised MANOBAL role: {raw_role!r}"
            raise ValueError(msg)

        amr = claims.get("amr") or []
        methods = frozenset(str(m).lower() for m in amr if isinstance(m, str))
        del second_factor_methods  # evaluated by the authenticator, not stored

        scopes_claim = claims.get("scope", "")
        scopes = frozenset(scopes_claim.split()) if isinstance(scopes_claim, str) else frozenset()

        return cls(
            actor_id=str(claims["sub"]),
            role=role,
            force_code=str(claims.get("force_code", "")),
            unit_code=str(claims.get("unit_code", "")),
            auth_methods=methods,
            scopes=scopes,
            subject_token=str(claims.get("subject_token", "")),
            session_id=str(claims.get("sid", "")),
        )
