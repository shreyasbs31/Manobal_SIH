import { PhoneFrame, SyntheticMarker } from "@manobal/ui";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Stage" };

const PHONES = new Set(["/app", "/app/saathi", "/app/toolkit", "/app/me"]);
const CONSOLES = new Set([
  "/command",
  "/command/roster",
  "/welfare",
  "/counsel",
  "/medical",
  "/hq",
  "/governance",
  "/lab",
]);

function safePath(value: unknown, allowed: Set<string>, fallback: string): string {
  if (typeof value !== "string") {
    return fallback;
  }
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("://")) {
    return fallback;
  }
  return allowed.has(value) ? value : fallback;
}

export default async function StagePage({
  searchParams,
}: {
  searchParams: Promise<{ phone?: string; console?: string }>;
}) {
  const params = await searchParams;
  const phone = safePath(params.phone, PHONES, "/app");
  const consolePath = safePath(params.console, CONSOLES, "/command");

  return (
    <div className="mb-stage">
      <div className="mb-stage-split">
        <PhoneFrame title="Saathi phone">
          <iframe src={phone} title="Saathi" />
        </PhoneFrame>
        <div className="mb-stage-console">
          <iframe src={consolePath} title="Command console" />
        </div>
      </div>
      <div className="mb-stage-drawer">
        <SyntheticMarker />
        <span>Phone {phone}</span>
        <span>Console {consolePath}</span>
        <Link className="mb-secondary" href="/director">
          Director
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/saathi&console=/welfare">
          Companion plus queue
        </Link>
      </div>
    </div>
  );
}
