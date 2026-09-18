import type { Metadata } from "next";

import { StageView } from "@/components/stage-view";

export const metadata: Metadata = { title: "Stage" };

export default async function StagePage({
  searchParams,
}: {
  searchParams: Promise<{
    phone?: string | undefined;
    console?: string | undefined;
    shot?: string | undefined;
    fixture?: string | undefined;
  }>;
}) {
  const params = await searchParams;
  const phone = params.fixture
    ? `${params.phone ?? "/app"}?fixture=${encodeURIComponent(params.fixture)}`
    : (params.phone ?? "/app");
  return (
    <StageView
      consolePath={params.console ?? "/command"}
      phonePath={phone}
      shot={params.shot}
    />
  );
}
