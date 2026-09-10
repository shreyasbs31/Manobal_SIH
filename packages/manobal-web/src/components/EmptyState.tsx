import type { ReactNode } from "react";

type Props = {
  title: string;
  children?: ReactNode;
};

export function EmptyState({ title, children }: Props) {
  return (
    <p className="empty">
      <strong>{title}</strong>
      {children ? <span>{children}</span> : null}
    </p>
  );
}
