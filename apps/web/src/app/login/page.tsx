import { PublicHeader } from "@manobal/ui";
import type { Metadata } from "next";

import { DemoLogin } from "@/components/demo-login";
import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = {
  title: "Sign in",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ role?: string }>;
}) {
  const params = await searchParams;
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-login">
        <h1>Sign in</h1>
        <p>
          Production personnel use a passkey or PIN. Officers use Entra ID.
          This demonstration mints the same scopes as those roles.
        </p>
        <DemoLogin initialRole={params.role} />
      </main>
    </div>
  );
}
