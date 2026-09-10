import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { InstrumentCatalogue, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

const CODES = ["phq9", "pss10", "gad7"] as const;

export function PersonnelInstruments({ session }: Props) {
  const api = createClient(session);
  const [code, setCode] = useState<(typeof CODES)[number]>("phq9");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [catalogue, setCatalogue] = useState<InstrumentCatalogue | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .instrumentCatalogue(code, lang)
      .then(setCatalogue)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "catalogue unavailable");
      });
  }, [session.token, code, lang]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!catalogue) return;
    const form = new FormData(event.currentTarget);
    const answers = catalogue.items.map((_, index) => Number(form.get(`item-${index}`)));
    const started = Number(form.get("started_at"));
    const result = await api.submitInstrument(
      code,
      lang,
      answers,
      Math.max(1, Math.round((Date.now() - started) / 1000)),
    );
    setTotal(result.total);
  }

  return (
    <section className="panel">
      <h2>Validated questionnaire</h2>
      <p className="muted">A total is kept. Individual answers are not stored.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="row">
        <label htmlFor="instrument-code">
          Instrument
          <select id="instrument-code" value={code} onChange={(event) => setCode(event.target.value as (typeof CODES)[number])}>
            {CODES.map((item) => (
              <option key={item} value={item}>
                {item.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="instrument-lang">
          Language
          <select id="instrument-lang" value={lang} onChange={(event) => setLang(event.target.value as "en" | "hi")}>
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
          </select>
        </label>
      </div>
      {catalogue ? (
        <form className="grid" onSubmit={(event) => void onSubmit(event)}>
          <input type="hidden" name="started_at" value={Date.now()} />
          <p>{catalogue.stem}</p>
          {catalogue.items.map((item, index) => (
            <fieldset key={`${catalogue.code}-${index}`}>
              <legend>{item}</legend>
              {catalogue.options.map((label, value) => (
                <label key={label} htmlFor={`item-${index}-${value}`}>
                  <input
                    id={`item-${index}-${value}`}
                    type="radio"
                    name={`item-${index}`}
                    value={value}
                    required={value === 0}
                    aria-required={value === 0 ? "true" : undefined}
                  />
                  {label}
                </label>
              ))}
            </fieldset>
          ))}
          <button type="submit">Submit</button>
        </form>
      ) : null}
      {total !== null ? <Notice>Recorded total: {total}. Item answers were discarded.</Notice> : null}
    </section>
  );
}
