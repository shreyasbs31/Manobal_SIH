import lexicon from "@/data/lexicon.json";

function normalise(text: string): string {
  return text
    .toLowerCase()
    .replace(/[''`´]/g, "")
    .replace(/[^\p{L}\p{N}\s]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function browserLexiconHit(text: string): boolean {
  const blob = normalise(text);
  const crisis = lexicon.crisis as Record<string, string[]>;
  return Object.values(crisis).some((phrases) =>
    phrases.some((phrase) => {
      const needle = normalise(phrase);
      return needle.length > 0 && blob.includes(needle);
    }),
  );
}

export function browserInjectionHit(text: string): boolean {
  const blob = normalise(text);
  return (lexicon.injection as string[]).some((phrase) => blob.includes(normalise(phrase)));
}
