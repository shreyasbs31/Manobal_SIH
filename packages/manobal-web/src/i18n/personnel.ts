export type PersonnelLang = "en" | "hi";

const COPY = {
  en: {
    eyebrow: "Personnel desk",
    title: "Your welfare record",
    lede: "Tier and category names only. No score is stored or shown.",
    picture: "Current picture",
    why: "Why this picture",
    next: "What to do next",
    engine: "How this picture works",
    streak: "Check-in streak",
    pictureMoved: "Today’s check-in changed the named picture.",
    pictureSame: "Today’s check-in is saved. The named picture is unchanged.",
    consent: "Consent",
    checkin: "Today’s check-in",
    help: "Need help now",
    helplineHint: "Helpline numbers are shown without creating a welfare record. SOS notifies an officer.",
    helplines: "Show helplines",
    sos: "Send SOS",
    trends: "Your trends",
    ledger: "Consent ledger",
    talk: "Talk",
    talkHint: "Crisis words never reach a model. A cloud listener replies when a key is configured.",
    thinking: "Listening on the unit server…",
    saved: "Saved. This is not a diagnosis.",
    language: "Language",
  },
  hi: {
    eyebrow: "कार्मिक डेस्क",
    title: "आपका कल्याण रिकॉर्ड",
    lede: "केवल स्तर और श्रेणी नाम। कोई अंक संग्रहीत या दिखाया नहीं जाता।",
    picture: "वर्तमान चित्र",
    why: "यह चित्र क्यों",
    next: "अब क्या करें",
    engine: "यह चित्र कैसे बनता है",
    streak: "लगातार जाँच",
    pictureMoved: "आज की जाँच ने नामित चित्र बदल दिया।",
    pictureSame: "आज की जाँच सहेजी गई। नामित चित्र वही है।",
    consent: "सहमति",
    checkin: "आज की जाँच",
    help: "अभी मदद चाहिए",
    helplineHint: "हेल्पलाइन नंबर बिना कल्याण रिकॉर्ड बनाए दिखते हैं। एसओएस अधिकारी को सूचित करता है।",
    helplines: "हेल्पलाइन दिखाएँ",
    sos: "एसओएस भेजें",
    trends: "आपके रुझान",
    ledger: "सहमति लेजर",
    talk: "बात करें",
    talkHint: "संकट शब्द मॉडल तक नहीं जाते। कुंजी होने पर क्लाउड श्रोता उत्तर देता है।",
    thinking: "इकाई सर्वर सुन रहा है…",
    saved: "सहेजा गया। यह निदान नहीं है।",
    language: "भाषा",
  },
} as const;

export function personnelCopy(lang: PersonnelLang) {
  return COPY[lang];
}

export function readPersonnelLang(): PersonnelLang {
  try {
    return window.localStorage.getItem("manobal.lang") === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}

export function storePersonnelLang(lang: PersonnelLang): void {
  try {
    window.localStorage.setItem("manobal.lang", lang);
  } catch {
    /* ignore quota / private mode */
  }
}
