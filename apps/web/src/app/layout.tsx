import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { OfflineObserver } from "@/components/offline-observer";
import { fontClassName } from "@/lib/fonts";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MANOBAL",
    template: "%s | MANOBAL",
  },
  description: "Support, not surveillance",
  applicationName: "MANOBAL",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#2f5d50",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html className={fontClassName} data-skin="saathi" data-theme="light" lang="en">
      <body>
        <OfflineObserver />
        {children}
      </body>
    </html>
  );
}
