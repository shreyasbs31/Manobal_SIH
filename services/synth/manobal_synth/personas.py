from __future__ import annotations

from pydantic import BaseModel


class SyntheticPersona(BaseModel):
    id: str
    case_id: str
    service_no: str
    token: str
    display_label: str
    language: str
    unit_path: str
    rank_band: str
    tenure_band: str
    phone: str
    posting: str
    gender: str
    home_region: str
    sector: str
    synthetic: bool = True


PERSONAS: tuple[SyntheticPersona, ...] = (
    SyntheticPersona(
        id="arjun",
        case_id="MB-4091",
        service_no="SYN-4091",
        token="st_364aifljnxnxpqzk",
        display_label="Ct/GD Arjun Rathore",
        language="hi",
        unit_path="force.central.c02.charlie",
        rank_band="Constable/GD",
        tenure_band="5_to_10",
        phone="SYN-PHONE-4091",
        posting="Charlie company synthetic post",
        gender="male",
        home_region="north_band",
        sector="central",
    ),
    SyntheticPersona(
        id="meena",
        case_id="MB-2217",
        service_no="SYN-2217",
        token="st_54dhr3kdu3njopjr",
        display_label="HC Meena Kumari",
        language="hi",
        unit_path="force.east.e01.alpha",
        rank_band="Head Constable",
        tenure_band="10_to_15",
        phone="SYN-PHONE-2217",
        posting="Alpha company synthetic post",
        gender="female",
        home_region="west_band",
        sector="east",
    ),
    SyntheticPersona(
        id="imran",
        case_id="MB-3380",
        service_no="SYN-3380",
        token="st_knqon22p4ahp64uu",
        display_label="Ct/GD Imran Sheikh",
        language="en",
        unit_path="force.north.n03.delta",
        rank_band="Constable/GD",
        tenure_band="0_to_5",
        phone="SYN-PHONE-3380",
        posting="Delta company synthetic post",
        gender="male",
        home_region="north_band",
        sector="north",
    ),
    SyntheticPersona(
        id="thomas",
        case_id="MB-1506",
        service_no="SYN-1506",
        token="st_xxvoccg2lkivzgxk",
        display_label="SI Thomas Varghese",
        language="en",
        unit_path="force.capital.c01.echo",
        rank_band="SI",
        tenure_band="15_plus",
        phone="SYN-PHONE-1506",
        posting="Echo company synthetic post",
        gender="male",
        home_region="south_band",
        sector="capital",
    ),
    SyntheticPersona(
        id="lalit",
        case_id="MB-5120",
        service_no="SYN-5120",
        token="st_pa3bwrpt2mffj52y",
        display_label="Ct/GD Lalit Oraon",
        language="hi",
        unit_path="force.central.c02.bravo",
        rank_band="Constable/GD",
        tenure_band="5_to_10",
        phone="SYN-PHONE-5120",
        posting="Bravo company synthetic post",
        gender="male",
        home_region="east_band",
        sector="central",
    ),
    SyntheticPersona(
        id="deepak",
        case_id="MB-6604",
        service_no="SYN-6604",
        token="st_ahe6nh4uupnem2wp",
        display_label="Ct/GD Deepak Negi",
        language="hi-Latn",
        unit_path="force.north.n01.foxtrot",
        rank_band="Constable/GD",
        tenure_band="5_to_10",
        phone="SYN-PHONE-6604",
        posting="Foxtrot company synthetic post",
        gender="male",
        home_region="north_band",
        sector="north",
    ),
    SyntheticPersona(
        id="rajesh",
        case_id="MB-7342",
        service_no="SYN-7342",
        token="st_kar3rtglz3ydm7uh",
        display_label="HC Rajesh Yadav",
        language="hi",
        unit_path="force.central.c03.delta",
        rank_band="Head Constable",
        tenure_band="10_to_15",
        phone="SYN-PHONE-7342",
        posting="Delta company synthetic post",
        gender="male",
        home_region="east_band",
        sector="central",
    ),
    SyntheticPersona(
        id="karthik",
        case_id="MB-8815",
        service_no="SYN-8815",
        token="st_gmtgrj5q2fihzscl",
        display_label="Ct/GD Karthik Selvam",
        language="ta",
        unit_path="force.east.e02.charlie",
        rank_band="Constable/GD",
        tenure_band="5_to_10",
        phone="SYN-PHONE-8815",
        posting="Charlie company synthetic post",
        gender="male",
        home_region="south_band",
        sector="east",
    ),
)


class PersonaPlaybook(BaseModel):
    id: str
    story: str
    expected_tier: str
    expected_levers: tuple[str, ...]
    consents: tuple[str, ...]
    helpers: tuple[str, ...]
    enrolled: bool
    wearable: bool
    voice: bool
    lifecycle_state: str
    family_separation_days: int = 0
    consecutive_duty_days: int = 0


PLAYBOOKS: dict[str, PersonaPlaybook] = {
    "arjun": PersonaPlaybook(
        id="arjun",
        story="19 consecutive duty days, night-shift volatility, sleep falling",
        expected_tier="T3",
        expected_levers=("REST_48H",),
        consents=("hr_derived", "self_report", "wearable", "ai_conversation"),
        helpers=("music", "talking"),
        enrolled=True,
        wearable=True,
        voice=False,
        lifecycle_state="inducted",
        consecutive_duty_days=19,
    ),
    "meena": PersonaPlaybook(
        id="meena",
        story="14 months at a non-family station, two leave rejections",
        expected_tier="T2",
        expected_levers=("LEAVE_PRIORITISE", "FAMILY_CONNECT"),
        consents=("hr_derived", "self_report"),
        helpers=("prayer", "family"),
        enrolled=True,
        wearable=False,
        voice=False,
        lifecycle_state="inducted",
        family_separation_days=420,
    ),
    "imran": PersonaPlaybook(
        id="imran",
        story="One bad week of sleep only",
        expected_tier="T1",
        expected_levers=("NO_ACTION",),
        consents=("hr_derived", "self_report", "wearable", "ai_conversation"),
        helpers=("sleep",),
        enrolled=True,
        wearable=True,
        voice=False,
        lifecycle_state="inducted",
    ),
    "thomas": PersonaPlaybook(
        id="thomas",
        story="Declined wearables and voice; stable",
        expected_tier="T0",
        expected_levers=("NO_ACTION",),
        consents=("hr_derived",),
        helpers=("reading",),
        enrolled=True,
        wearable=False,
        voice=False,
        lifecycle_state="inducted",
    ),
    "lalit": PersonaPlaybook(
        id="lalit",
        story="Unit IED incident on D-3",
        expected_tier="T1",
        expected_levers=("POST_INCIDENT_CHECKIN",),
        consents=("hr_derived", "self_report", "ai_conversation"),
        helpers=("sport", "talking"),
        enrolled=True,
        wearable=False,
        voice=False,
        lifecycle_state="inducted",
    ),
    "deepak": PersonaPlaybook(
        id="deepak",
        story="Distress message on D0 opens the acute path",
        expected_tier="T0",
        expected_levers=("NO_ACTION",),
        consents=(
            "hr_derived",
            "self_report",
            "wearable",
            "voice_features",
            "ai_conversation",
        ),
        helpers=("talking",),
        enrolled=True,
        wearable=True,
        voice=True,
        lifecycle_state="inducted",
    ),
    "rajesh": PersonaPlaybook(
        id="rajesh",
        story="Land dispute, grievance pending 60 days, duty swaps rising",
        expected_tier="T2",
        expected_levers=("GRIEVANCE_EXPEDITE", "LEGAL_AID_REFERRAL"),
        consents=("hr_derived", "self_report"),
        helpers=("talking",),
        enrolled=True,
        wearable=False,
        voice=False,
        lifecycle_state="inducted",
    ),
    "karthik": PersonaPlaybook(
        id="karthik",
        story="Return from 35 days of leave after a family bereavement",
        expected_tier="T1",
        expected_levers=("REINTEGRATION_CHAT",),
        consents=("hr_derived", "self_report", "ai_conversation"),
        helpers=("walking", "writing"),
        enrolled=True,
        wearable=False,
        voice=True,
        lifecycle_state="return_from_leave",
    ),
}
