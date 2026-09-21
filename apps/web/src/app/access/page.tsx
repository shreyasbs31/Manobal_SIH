import { PublicHeader } from "@manobal/ui";
import type { Metadata } from "next";

import { AccessForm } from "@/app/access/access-form";
import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = {
  title: "Judge access",
};

function safeNextPath(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }
  if (value.startsWith("/access")) {
    return "/";
  }
  return value;
}

export default async function AccessPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-login">
        <h1>Judge access</h1>
        <p>
          This is a shared demonstration containing synthetic people and
          synthetic cases. Actions can change the sandbox for other reviewers.
        </p>
        <AccessForm nextPath={safeNextPath(params.next)} />
      </main>
    </div>
  );
}
