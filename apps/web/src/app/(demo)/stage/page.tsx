import type { Metadata } from "next";

import { StageView } from "@/components/stage-view";

export const metadata: Metadata = { title: "Stage" };

export default async function StagePage({
  searchParams,
}: {
  searchParams: Promise<{ phone?: string; console?: string }>;
}) {
  const params = await searchParams;
  return (
    <StageView
      consolePath={params.console ?? "/command"}
      phonePath={params.phone ?? "/app"}
    />
  );
}
