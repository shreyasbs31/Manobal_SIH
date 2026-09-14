import type { InsightAction } from "../api/types";

type Props = { items: InsightAction[] };

export function NextActions({ items }: Props) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="action-grid">
      {items.map((item) => (
        <a key={item.id} className="action-card" href={`#${item.href}`}>
          <strong>{item.title}</strong>
          <span>{item.detail}</span>
        </a>
      ))}
    </div>
  );
}
