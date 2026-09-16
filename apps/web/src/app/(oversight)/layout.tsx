import type { ReactNode } from "react";

import { ConsoleChrome } from "@/components/console-chrome";

export default function OversightLayout({ children }: { children: ReactNode }) {
  return <ConsoleChrome>{children}</ConsoleChrome>;
}
