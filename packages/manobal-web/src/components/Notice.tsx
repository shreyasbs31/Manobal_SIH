import type { ReactNode } from "react";

type Props = {
  tone?: "info" | "error";
  children: ReactNode;
};

export function Notice({ tone = "info", children }: Props) {
  return (
    <div className={tone === "error" ? "error" : "banner"} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
