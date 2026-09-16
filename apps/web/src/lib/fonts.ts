import {
  Anek_Devanagari,
  Anek_Latin,
  Mukta,
  Noto_Nastaliq_Urdu,
  Noto_Sans,
  Noto_Sans_Bengali,
  Noto_Sans_Gujarati,
  Noto_Sans_Gurmukhi,
  Noto_Sans_Kannada,
  Noto_Sans_Malayalam,
  Noto_Sans_Oriya,
  Noto_Sans_Tamil,
  Noto_Sans_Telugu,
} from "next/font/google";

const anek = Anek_Latin({
  subsets: ["latin"],
  display: "swap",
  axes: ["wdth"],
  variable: "--font-anek",
});

const anekDeva = Anek_Devanagari({
  subsets: ["devanagari"],
  display: "swap",
  preload: false,
  axes: ["wdth"],
  variable: "--font-anek-deva",
});

const mukta = Mukta({
  subsets: ["latin", "devanagari"],
  weight: ["400", "600", "700"],
  display: "swap",
  variable: "--font-mukta",
});

const noto = Noto_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600"],
  display: "swap",
  preload: false,
  variable: "--font-noto",
});

const notoTa = Noto_Sans_Tamil({
  subsets: ["tamil"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-ta",
});

const notoTe = Noto_Sans_Telugu({
  subsets: ["telugu"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-te",
});

const notoKn = Noto_Sans_Kannada({
  subsets: ["kannada"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-kn",
});

const notoMl = Noto_Sans_Malayalam({
  subsets: ["malayalam"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-ml",
});

const notoGu = Noto_Sans_Gujarati({
  subsets: ["gujarati"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-gu",
});

const notoPa = Noto_Sans_Gurmukhi({
  subsets: ["gurmukhi"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-pa",
});

const notoOr = Noto_Sans_Oriya({
  subsets: ["oriya"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-or",
});

const notoBn = Noto_Sans_Bengali({
  subsets: ["bengali"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-bn",
});

const notoUr = Noto_Nastaliq_Urdu({
  subsets: ["arabic"],
  weight: ["400", "700"],
  display: "swap",
  preload: false,
  variable: "--font-noto-ur",
});

export const fontClassName = [
  anek.variable,
  anekDeva.variable,
  mukta.variable,
  noto.variable,
  notoTa.variable,
  notoTe.variable,
  notoKn.variable,
  notoMl.variable,
  notoGu.variable,
  notoPa.variable,
  notoOr.variable,
  notoBn.variable,
  notoUr.variable,
].join(" ");
