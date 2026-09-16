import type { ReactNode } from "react";

import type { Skin, ThemeName } from "./types";

export function ThemeRoot({
  skin,
  theme,
  children,
  className,
}: {
  skin: Skin;
  theme: ThemeName;
  children: ReactNode;
  className?: string | undefined;
}) {
  const resolved: ThemeName =
    skin === "command" && theme === "hc" ? "dark" : theme;
  return (
    <div
      className={className ? `mb-theme ${className}` : "mb-theme"}
      data-skin={skin}
      data-theme={resolved}
    >
      {children}
    </div>
  );
}
