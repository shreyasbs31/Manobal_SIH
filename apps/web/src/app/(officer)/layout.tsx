import type { ReactNode } from "react";

import { ConsoleChrome } from "@/components/console-chrome";

export default function OfficerLayout({ children }: { children: ReactNode }) {
  return <ConsoleChrome>{children}</ConsoleChrome>;
}
