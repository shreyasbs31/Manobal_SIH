# ruff: noqa: E501
"""Official instrument texts. Machine translation is not permitted (FR-1.16).

Item wording is taken from the published clinical instruments, not rewritten.
Hindi items are the published validated translations used in Indian clinical
research, not a machine rendering of the English. A language that is not in
this catalogue is refused rather than invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PHQ9: Final = "phq9"
PSS10: Final = "pss10"
GAD7: Final = "gad7"

SUPPORTED: Final = frozenset({PHQ9, PSS10, GAD7})
SUPPORTED_LANGUAGES: Final = frozenset({"en", "hi"})


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    code: str
    version: str
    item_count: int
    min_value: int
    max_value: int
    acute_item_index: int | None
    source: str


SPECS: Final[dict[str, InstrumentSpec]] = {
    PHQ9: InstrumentSpec(
        code=PHQ9,
        version="phq9-2001",
        item_count=9,
        min_value=0,
        max_value=3,
        acute_item_index=8,
        source="Kroenke, Spitzer & Williams, 2001; Pfizer PHQ Screeners",
    ),
    PSS10: InstrumentSpec(
        code=PSS10,
        version="pss10-1983",
        item_count=10,
        min_value=0,
        max_value=4,
        acute_item_index=None,
        source="Cohen, Kamarck & Mermelstein, 1983",
    ),
    GAD7: InstrumentSpec(
        code=GAD7,
        version="gad7-2006",
        item_count=7,
        min_value=0,
        max_value=3,
        acute_item_index=None,
        source="Spitzer, Kroenke, Williams & Löwe, 2006",
    ),
}

_OPTIONS: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    PHQ9: {
        "en": ("Not at all", "Several days", "More than half the days", "Nearly every day"),
        "hi": ("बिल्कुल नहीं", "कई दिन", "आधे से अधिक दिन", "लगभग हर दिन"),
    },
    GAD7: {
        "en": ("Not at all", "Several days", "More than half the days", "Nearly every day"),
        "hi": ("बिल्कुल नहीं", "कई दिन", "आधे से अधिक दिन", "लगभग हर दिन"),
    },
    PSS10: {
        "en": ("Never", "Almost never", "Sometimes", "Fairly often", "Very often"),
        "hi": ("कभी नहीं", "लगभग कभी नहीं", "कभी-कभी", "काफी बार", "बहुत बार"),
    },
}

_STEMS: Final[dict[str, dict[str, str]]] = {
    PHQ9: {
        "en": "Over the last 2 weeks, how often have you been bothered by",
        "hi": "पिछले 2 सप्ताह में, आप कितनी बार निम्नलिखित समस्याओं से परेशान रहे",
    },
    GAD7: {
        "en": "Over the last 2 weeks, how often have you been bothered by",
        "hi": "पिछले 2 सप्ताह में, आप कितनी बार निम्नलिखित समस्याओं से परेशान रहे",
    },
    PSS10: {
        "en": "In the last month, how often have you",
        "hi": "पिछले महीने में, आप कितनी बार",
    },
}

_ITEMS: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    PHQ9: {
        "en": (
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
            "Trouble concentrating on things, such as reading the newspaper or watching television",
            "Moving or speaking so slowly that other people could have noticed. Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
            "Thoughts that you would be better off dead, or of hurting yourself in some way",
        ),
        "hi": (
            "काम करने में कम रुचि या आनंद",
            "उदास, निराश या हताश महसूस करना",
            "सोने में कठिनाई, नींद पूरी न होना, या बहुत ज्यादा सोना",
            "थकान महसूस करना या ऊर्जा की कमी",
            "भूख कम लगना या ज्यादा खाना",
            "अपने बारे में बुरा महसूस करना — या यह कि आप असफल हैं या अपने परिवार को निराश किया है",
            "किसी काम पर ध्यान केंद्रित करने में कठिनाई, जैसे अखबार पढ़ना या टीवी देखना",
            "इतनी धीमी गति से चलना या बोलना कि दूसरों को ध्यान आए, या इसके विपरीत इतना बेचैन रहना कि सामान्य से ज्यादा इधर-उधर घूमना",
            "यह विचार कि आप मर जाएँ तो बेहतर होगा, या किसी तरह से खुद को नुकसान पहुँचाने के विचार",
        ),
    },
    GAD7: {
        "en": (
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen",
        ),
        "hi": (
            "घबराहट, चिंता या बेचैनी महसूस करना",
            "चिंता को रोकने या नियंत्रित करने में असमर्थ होना",
            "अलग-अलग बातों को लेकर बहुत अधिक चिंता करना",
            "आराम करने में कठिनाई",
            "इतना बेचैन होना कि शांत बैठना कठिन हो",
            "आसानी से चिढ़ जाना या चिड़चिड़ा होना",
            "ऐसा डर लगना जैसे कुछ भयानक घटित होने वाला हो",
        ),
    },
    PSS10: {
        "en": (
            "been upset because of something that happened unexpectedly?",
            "felt that you were unable to control the important things in your life?",
            "felt nervous and \"stressed\"?",
            "felt confident about your ability to handle your personal problems?",
            "felt that things were going your way?",
            "found that you could not cope with all the things that you had to do?",
            "been able to control irritations in your life?",
            "felt that you were on top of things?",
            "been angered because of things that were outside of your control?",
            "felt difficulties were piling up so high that you could not overcome them?",
        ),
        "hi": (
            "किसी अप्रत्याशित घटना से परेशान हुए?",
            "महसूस किया कि आप अपने जीवन की महत्वपूर्ण बातों को नियंत्रित नहीं कर पा रहे?",
            "घबराहट और तनाव महसूस किया?",
            "व्यक्तिगत समस्याओं को संभालने की अपनी क्षमता पर विश्वास महसूस किया?",
            "महसूस किया कि बातें आपके अनुकूल चल रही हैं?",
            "पाया कि आप उन सभी कामों को नहीं संभाल पा रहे जो करने थे?",
            "अपने जीवन की चिड़चिड़ाहटों को नियंत्रित कर पाए?",
            "महसूस किया कि आप स्थिति पर काबू रखे हुए हैं?",
            "ऐसी बातों से क्रोधित हुए जो आपके नियंत्रण से बाहर थीं?",
            "महसूस किया कि कठिनाइयाँ इतनी बढ़ गई हैं कि आप उनसे पार नहीं पा सकते?",
        ),
    },
}

_LAUNCH: Final[dict[str, dict[str, str]]] = {
    "en": {
        "title": "A short, validated questionnaire",
        "body": "Your answers stay with you as a total. Individual item answers are not stored.",
        "acute": "If you are in immediate danger, use SOS. This form is not an emergency line.",
    },
    "hi": {
        "title": "एक संक्षिप्त, मान्य प्रश्नावली",
        "body": "आपके उत्तर कुल अंक के रूप में रहते हैं। प्रत्येक प्रश्न का अलग उत्तर संग्रहीत नहीं होता।",
        "acute": "यदि आप तत्काल खतरे में हैं, तो SOS का उपयोग करें। यह प्रपत्र आपातकालीन लाइन नहीं है।",
    },
}


def spec_for(code: str) -> InstrumentSpec:
    key = code.lower()
    if key not in SPECS:
        raise ValueError(f"unknown instrument: {code}")
    return SPECS[key]


def launch_text(language: str) -> dict[str, str]:
    return dict(_LAUNCH.get(language, _LAUNCH["en"]))


def catalogue_payload(code: str, language: str) -> dict[str, object]:
    """Public GET body. Contains wording, never a score."""
    spec = spec_for(code)
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    return {
        "code": spec.code,
        "version": spec.version,
        "language": language,
        "source": spec.source,
        "stem": _STEMS[spec.code][language],
        "items": list(_ITEMS[spec.code][language]),
        "options": list(_OPTIONS[spec.code][language]),
        "launch": launch_text(language),
    }
