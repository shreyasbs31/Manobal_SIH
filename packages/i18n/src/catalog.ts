export const EN_STRINGS: Record<string, string> = {
  "home.checkin.title": "How are you after duty?",
  "home.lay.within": "You are within your usual rhythm.",
  "home.lay.sleepLow": "Your sleep has been below your usual rhythm for {n} nights.",
  "safety.title": "You are not alone.",
  "safety.reaching": "Someone is being asked to reach you.",
  "privacy.commander": "Your commander never sees you.",
  "checkin.saved": "Saved. Thank you for checking in.",
  "offline.bar": "Offline. {n} check-ins saved on this phone.",
};

export const HI_STRINGS: Record<string, string> = {
  "home.checkin.title": "ड्यूटी के बाद आप कैसा महसूस कर रहे हैं?",
  "home.lay.within": "आप अपनी सामान्य लय में हैं।",
  "home.lay.sleepLow": "पिछली {n} रातों से आपकी नींद सामान्य से कम रही है।",
  "safety.title": "आप अकेले नहीं हैं।",
  "safety.reaching": "किसी को आपसे संपर्क करने के लिए कहा जा रहा है।",
  "privacy.commander": "आपके कमांडर आपको कभी व्यक्तिगत रूप से नहीं देखते।",
  "checkin.saved": "सहेज लिया गया। चेक-इन करने के लिए धन्यवाद।",
  "offline.bar": "ऑफ़लाइन। {n} चेक-इन इस फ़ोन पर सहेजे गए हैं।",
};

export const TA_STRINGS: Record<string, string> = {
  "home.checkin.title": "கடமைக்குப் பிறகு நீங்கள் எப்படி இருக்கிறீர்கள்?",
  "home.lay.within": "நீங்கள் உங்கள் வழக்கமான தாளத்தில் இருக்கிறீர்கள்.",
  "home.lay.sleepLow": "கடந்த {n} இரவுகளாக உங்கள் உறக்கம் வழக்கத்தை விட குறைவு.",
  "safety.title": "நீங்கள் தனியாக இல்லை.",
  "safety.reaching": "உங்களை அணுக ஒரு நபரிடம் கேட்கப்பட்டுள்ளது.",
  "privacy.commander": "உங்கள் கமாண்டர் உங்களை ஒருபோதும் தனிப்பட்ட முறையில் பார்ப்பதில்லை.",
  "checkin.saved": "சேமிக்கப்பட்டது. பார்த்துக் கொண்டதற்கு நன்றி.",
  "offline.bar": "ஆஃப்லைன். இந்த தொலைபேசியில் {n} செக்-இன் சேமிக்கப்பட்டுள்ளன.",
  "home.greeting.karthik": "வணக்கம், கார்த்திக்",
};

const TABLES: Record<string, Record<string, string>> = {
  en: EN_STRINGS,
  hi: HI_STRINGS,
  ta: TA_STRINGS,
};

export function reviewedLang(lang: string): boolean {
  return lang === "en" || lang === "hi" || lang === "ta";
}

export function t(key: string, lang: string, vars: Record<string, string | number> = {}): string {
  const table = TABLES[lang] ?? EN_STRINGS;
  let template = table[key] ?? EN_STRINGS[key] ?? key;
  for (const [name, value] of Object.entries(vars)) {
    template = template.replaceAll(`{${name}}`, String(value));
  }
  return template;
}

export function machineTranslated(lang: string): boolean {
  return !reviewedLang(lang);
}
