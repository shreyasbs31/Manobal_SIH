export interface LanguageDefinition {
  tag: string;
  label: string;
  direction: "ltr" | "rtl";
  scheduled: boolean;
  reviewed: boolean;
}

export const languages = [
  { tag: "as", label: "অসমীয়া", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "bn", label: "বাংলা", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "brx", label: "बड़ो", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "doi", label: "डोगरी", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "gu", label: "ગુજરાતી", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "hi", label: "हिन्दी", direction: "ltr", scheduled: true, reviewed: true },
  { tag: "kn", label: "ಕನ್ನಡ", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "ks", label: "کٲشُر", direction: "rtl", scheduled: true, reviewed: false },
  { tag: "kok", label: "कोंकणी", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "mai", label: "मैथिली", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "ml", label: "മലയാളം", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "mni", label: "মৈতৈলোন্", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "mr", label: "मराठी", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "ne", label: "नेपाली", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "or", label: "ଓଡ଼ିଆ", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "pa", label: "ਪੰਜਾਬੀ", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "sa", label: "संस्कृतम्", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "sat", label: "ᱥᱟᱱᱛᱟᱲᱤ", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "sd", label: "سنڌي", direction: "rtl", scheduled: true, reviewed: false },
  { tag: "ta", label: "தமிழ்", direction: "ltr", scheduled: true, reviewed: true },
  { tag: "te", label: "తెలుగు", direction: "ltr", scheduled: true, reviewed: false },
  { tag: "ur", label: "اردو", direction: "rtl", scheduled: true, reviewed: false },
  { tag: "en", label: "English", direction: "ltr", scheduled: false, reviewed: true },
] as const satisfies readonly LanguageDefinition[];

export type LanguageTag = (typeof languages)[number]["tag"];

export { machineTranslated, reviewedLang, t } from "./catalog";
export { EN_STRINGS, HI_STRINGS, TA_STRINGS } from "./catalog";

