const SLEEP_WORDS = ["", "Broken", "Thin", "Fair", "Solid", "Rested"] as const;

type Point = {
  observed_on: string;
  sleep_quality?: number | null;
  mood?: number | null;
};

type Props = { points: Point[] };

export function WeekStrip({ points }: Props) {
  const week = [...points].slice(0, 7).reverse();
  if (!week.length) {
    return null;
  }
  return (
    <div className="week-strip" aria-label="This week’s sleep check-ins">
      {week.map((row) => {
        const sleep = row.sleep_quality ?? row.mood ?? 1;
        return (
          <div key={row.observed_on} className="week-day">
            <span
              className="week-bar"
              style={{ height: `${10 + sleep * 10}px` }}
              aria-hidden="true"
            />
            <small>{row.observed_on.slice(5)}</small>
            <small>{SLEEP_WORDS[sleep] ?? ""}</small>
          </div>
        );
      })}
    </div>
  );
}
