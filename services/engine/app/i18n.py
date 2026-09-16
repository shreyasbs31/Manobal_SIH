from __future__ import annotations

from typing import Any

REVIEWED = frozenset({"en", "hi"})

EN: dict[str, str] = {
    "home.checkin.title": "How are you after duty?",
    "home.lay.within": "You are within your usual rhythm.",
    "home.lay.sleepLow": "Your sleep has been below your usual rhythm for {n} nights.",
    "safety.title": "You are not alone.",
    "safety.reaching": "Someone is being asked to reach you.",
    "privacy.commander": "Your commander never sees you.",
    "checkin.saved": "Saved. Thank you for checking in.",
    "offline.bar": "Offline. {n} check-ins saved on this phone.",
    "onboarding.support": "Support, not surveillance",
    "onboarding.commander": "Your commander never sees you",
    "onboarding.control": "You control your data",
    "exception.body": (
        "If you are in immediate danger, a welfare officer and a medical officer "
        "are asked to reach you. That is the one exception. Your commander still "
        "does not see your check-ins or talks with Saathi."
    ),
    "home.greeting.arjun": "Suprabhat, Arjun",
    "home.greeting.meena": "Namaste, Meena",
    "home.greeting.karthik": "Vanakkam, Karthik",
}

HI: dict[str, str] = {
    "home.checkin.title": "ड्यूटी के बाद आप कैसा महसूस कर रहे हैं?",
    "home.lay.within": "आप अपनी सामान्य लय में हैं।",
    "home.lay.sleepLow": "पिछली {n} रातों से आपकी नींद सामान्य से कम रही है।",
    "safety.title": "आप अकेले नहीं हैं।",
    "safety.reaching": "किसी को आपसे संपर्क करने के लिए कहा जा रहा है।",
    "privacy.commander": "आपके कमांडर आपको कभी व्यक्तिगत रूप से नहीं देखते।",
    "checkin.saved": "सहेज लिया गया। चेक-इन करने के लिए धन्यवाद।",
    "offline.bar": "ऑफ़लाइन। {n} चेक-इन इस फ़ोन पर सहेजे गए हैं।",
    "onboarding.support": "सहारा, निगरानी नहीं",
    "onboarding.commander": "आपके कमांडर आपको कभी व्यक्तिगत रूप से नहीं देखते",
    "onboarding.control": "आप अपने डेटा को नियंत्रित करते हैं",
    "exception.body": (
        "अगर आप तुरंत खतरे में हैं, तो कल्याण अधिकारी और चिकित्सा अधिकारी से "
        "आप तक पहुँचने के लिए कहा जाता है। यही एकमात्र अपवाद है। आपके कमांडर "
        "आपके चेक-इन या साथी से बात नहीं देखते।"
    ),
    "home.greeting.arjun": "सुप्रभात, अर्जुन",
    "home.greeting.meena": "नमस्ते, मीना",
    "home.greeting.karthik": "வனக்கம், கார்த்திக்",
}

TA: dict[str, str] = {
    "home.checkin.title": "கடமைக்குப் பிறகு நீங்கள் எப்படி இருக்கிறீர்கள்?",
    "home.lay.within": "நீங்கள் உங்கள் வழக்கமான தாளத்தில் இருக்கிறீர்கள்.",
    "home.lay.sleepLow": "கடந்த {n} இரவுகளாக உங்கள் உறக்கம் வழக்கத்தை விட குறைவு.",
    "safety.title": "நீங்கள் தனியாக இல்லை.",
    "safety.reaching": "உங்களை அணுக ஒரு நபரிடம் கேட்கப்பட்டுள்ளது.",
    "privacy.commander": "உங்கள் கமாண்டர் உங்களை ஒருபோதும் தனிப்பட்ட முறையில் பார்ப்பதில்லை.",
    "checkin.saved": "சேமிக்கப்பட்டது. பார்த்துக் கொண்டதற்கு நன்றி.",
    "offline.bar": "ஆஃப்லைன். இந்த தொலைபேசியில் {n} செக்-இன் சேமிக்கப்பட்டுள்ளன.",
    "home.greeting.karthik": "வணக்கம், கார்த்திக்",
    "onboarding.support": "ஆதரவு, கண்காணிப்பு அல்ல",
    "onboarding.commander": "உங்கள் கமாண்டர் உங்களை ஒருபோதும் பார்ப்பதில்லை",
    "onboarding.control": "உங்கள் தரவை நீங்களே கட்டுப்படுத்துகிறீர்கள்",
    "exception.body": EN["exception.body"],
}

CATALOG: dict[str, dict[str, str]] = {"en": EN, "hi": HI, "ta": TA}

SCHEDULED = (
    "as",
    "bn",
    "brx",
    "doi",
    "gu",
    "hi",
    "kn",
    "ks",
    "kok",
    "mai",
    "ml",
    "mni",
    "mr",
    "ne",
    "or",
    "pa",
    "sa",
    "sat",
    "sd",
    "ta",
    "te",
    "ur",
)


def reviewed(lang: str) -> bool:
    return lang in REVIEWED or lang == "ta"


def t(key: str, lang: str, **kwargs: object) -> str:
    table = CATALOG.get(lang) or EN
    template = table.get(key) or EN.get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


def catalog_for(lang: str) -> dict[str, Any]:
    machine = lang not in REVIEWED and lang != "ta"
    table = dict(EN)
    if lang in CATALOG:
        table.update(CATALOG[lang])
    return {
        "lang": lang,
        "reviewed": reviewed(lang),
        "machine_translated": machine,
        "strings": table,
    }
