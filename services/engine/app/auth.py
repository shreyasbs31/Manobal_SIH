from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from pydantic import BaseModel

from .config import Settings, get_settings
from .errors import ApiError


class Role(StrEnum):
    PERSONNEL = "personnel"
    UWO = "uwo"
    COUNSELLOR = "counsellor"
    MO = "mo"
    COMMANDER = "commander"
    HQ = "hq"
    WDEC = "wdec"
    DPO = "dpo"
    HRMS_INTEGRATOR = "hrms_integrator"
    ADMIN = "admin"
    DIRECTOR = "director"


class Persona(BaseModel):
    id: str
    case_id: str
    display_label: str
    token: str
    language: str
    unit_path: str
    synthetic: bool = True


PERSONAS: dict[str, Persona] = {
    "arjun": Persona(
        id="arjun",
        case_id="MB-4091",
        display_label="Ct/GD Arjun Rathore",
        token="st_364aifljnxnxpqzk",
        language="hi",
        unit_path="force.central.c02.charlie",
    ),
    "meena": Persona(
        id="meena",
        case_id="MB-2217",
        display_label="HC Meena Kumari",
        token="st_54dhr3kdu3njopjr",
        language="hi",
        unit_path="force.east.e01.alpha",
    ),
    "imran": Persona(
        id="imran",
        case_id="MB-3380",
        display_label="Ct/GD Imran Sheikh",
        token="st_knqon22p4ahp64uu",
        language="en",
        unit_path="force.north.n03.delta",
    ),
    "thomas": Persona(
        id="thomas",
        case_id="MB-1506",
        display_label="SI Thomas Varghese",
        token="st_xxvoccg2lkivzgxk",
        language="en",
        unit_path="force.capital.c01.echo",
    ),
    "lalit": Persona(
        id="lalit",
        case_id="MB-5120",
        display_label="Ct/GD Lalit Oraon",
        token="st_pa3bwrpt2mffj52y",
        language="hi",
        unit_path="force.central.c02.bravo",
    ),
    "deepak": Persona(
        id="deepak",
        case_id="MB-6604",
        display_label="Ct/GD Deepak Negi",
        token="st_ahe6nh4uupnem2wp",
        language="hi-Latn",
        unit_path="force.north.n01.foxtrot",
    ),
    "rajesh": Persona(
        id="rajesh",
        case_id="MB-7342",
        display_label="HC Rajesh Yadav",
        token="st_kar3rtglz3ydm7uh",
        language="hi",
        unit_path="force.central.c03.delta",
    ),
    "karthik": Persona(
        id="karthik",
        case_id="MB-8815",
        display_label="Ct/GD Karthik Selvam",
        token="st_gmtgrj5q2fihzscl",
        language="ta",
        unit_path="force.east.e02.charlie",
    ),
}


class OfficerPersona(BaseModel):
    id: str
    display_label: str
    role: Role
    unit_path: str
    synthetic: bool = True


OFFICER_PERSONAS: dict[Role, OfficerPersona] = {
    Role.UWO: OfficerPersona(
        id="uwo-sunita",
        display_label="Insp. Sunita Rawat",
        role=Role.UWO,
        unit_path="force",
    ),
    Role.COUNSELLOR: OfficerPersona(
        id="counsellor-anjali",
        display_label="Ms. Anjali Deshmukh",
        role=Role.COUNSELLOR,
        unit_path="force.central",
    ),
    Role.MO: OfficerPersona(
        id="mo-farah",
        display_label="Dr. Farah Siddiqui",
        role=Role.MO,
        unit_path="force.north.n01",
    ),
    Role.COMMANDER: OfficerPersona(
        id="commander-menon",
        display_label="Commandant R. K. Menon",
        role=Role.COMMANDER,
        unit_path="force.central.c02",
    ),
    Role.HQ: OfficerPersona(
        id="hq-central",
        display_label="IG Synthetic Sector Central",
        role=Role.HQ,
        unit_path="force",
    ),
    Role.WDEC: OfficerPersona(
        id="wdec-kavita",
        display_label="Dr. Kavita Rao",
        role=Role.WDEC,
        unit_path="force",
    ),
    Role.DPO: OfficerPersona(
        id="dpo-synthetic",
        display_label="DPO Synthetic",
        role=Role.DPO,
        unit_path="force",
    ),
    Role.HRMS_INTEGRATOR: OfficerPersona(
        id="integrator-synthetic",
        display_label="HRMS custodian Synthetic",
        role=Role.HRMS_INTEGRATOR,
        unit_path="force",
    ),
    Role.ADMIN: OfficerPersona(
        id="admin-synthetic",
        display_label="System admin Synthetic",
        role=Role.ADMIN,
        unit_path="force",
    ),
    Role.DIRECTOR: OfficerPersona(
        id="director-synthetic",
        display_label="Demo director Synthetic",
        role=Role.DIRECTOR,
        unit_path="force",
    ),
}

ROLE_SCOPES: dict[Role, frozenset[str]] = {
    Role.PERSONNEL: frozenset({"system:read", "me:read", "me:write"}),
    Role.UWO: frozenset({"system:read", "welfare:read", "welfare:write"}),
    Role.COUNSELLOR: frozenset({"system:read", "counsel:read", "counsel:write"}),
    Role.MO: frozenset({"system:read", "medical:read", "medical:write"}),
    Role.COMMANDER: frozenset({"system:read", "command:aggregate"}),
    Role.HQ: frozenset({"system:read", "hq:aggregate"}),
    Role.WDEC: frozenset({"system:read", "gov:read", "gov:write"}),
    Role.DPO: frozenset({"system:read", "dpo:read", "dpo:write"}),
    Role.HRMS_INTEGRATOR: frozenset({"system:read", "integrations:read", "integrations:write"}),
    Role.ADMIN: frozenset({"system:read", "admin:read", "admin:write"}),
    Role.DIRECTOR: frozenset({"system:read", "demo:write"}),
}


class Principal(BaseModel):
    actor_id: str
    role: Role
    scopes: frozenset[str]
    scope_path: str
    subject_token: str | None = None
    synthetic: bool = True


class DemoLoginRequest(BaseModel):
    role: Role
    persona_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    principal: Principal


def principal_for_demo(request: DemoLoginRequest) -> Principal:
    if request.role is Role.PERSONNEL:
        persona_id = request.persona_id or "arjun"
        persona = PERSONAS.get(persona_id)
        if persona is None:
            raise ApiError(
                "persona_not_found",
                "The synthetic persona was not found",
                hint="Choose one of the listed demo personas",
                status_code=404,
            )
        return Principal(
            actor_id=f"demo:{persona.id}",
            role=Role.PERSONNEL,
            scopes=ROLE_SCOPES[Role.PERSONNEL],
            scope_path=persona.unit_path,
            subject_token=persona.token,
        )

    officer = OFFICER_PERSONAS[request.role]
    return Principal(
        actor_id=officer.id,
        role=request.role,
        scopes=ROLE_SCOPES[request.role],
        scope_path=officer.unit_path,
    )


def mint_access_token(
    principal: Principal,
    settings: Settings | None = None,
) -> LoginResponse:
    active_settings = settings or get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=active_settings.access_token_minutes)
    claims: dict[str, object] = {
        "iss": "manobal-engine",
        "aud": "manobal-web",
        "sub": principal.actor_id,
        "role": principal.role.value,
        "scopes": sorted(principal.scopes),
        "scope_path": principal.scope_path,
        "synthetic": principal.synthetic,
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    if principal.subject_token is not None:
        claims["subject_token"] = principal.subject_token
    token = jwt.encode(
        claims,
        active_settings.access_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return LoginResponse(
        access_token=token,
        expires_in=int((expires - now).total_seconds()),
        principal=principal,
    )


def decode_access_token(
    token: str,
    settings: Settings | None = None,
) -> Principal:
    active_settings = settings or get_settings()
    try:
        claims = jwt.decode(
            token,
            active_settings.access_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="manobal-web",
            issuer="manobal-engine",
        )
        role = Role(str(claims["role"]))
        scopes_claim = claims.get("scopes", [])
        if not isinstance(scopes_claim, list):
            raise ValueError("scopes")
        return Principal(
            actor_id=str(claims["sub"]),
            role=role,
            scopes=frozenset(str(scope) for scope in scopes_claim),
            scope_path=str(claims["scope_path"]),
            subject_token=(
                str(claims["subject_token"]) if claims.get("subject_token") is not None else None
            ),
            synthetic=bool(claims.get("synthetic", False)),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise ApiError(
            "invalid_token",
            "The access token is invalid or expired",
            hint="Sign in again",
            status_code=401,
        ) from error
