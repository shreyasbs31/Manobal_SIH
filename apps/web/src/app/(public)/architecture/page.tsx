import { PublicHeader, ZoneDiagram } from "@manobal/ui";
import type { Metadata } from "next";

import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = { title: "Architecture" };

export default function ArchitecturePage() {
  return (
    <div className="mb-theme" data-skin="command" data-theme="dark">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-command-body">
        <h1>Separated by design</h1>
        <p>
          Live self-tests prove the engine cannot reach identity storage or its
          keys. Command routes never accept a person, case, or token parameter.
        </p>
        <ZoneDiagram />
      </main>
    </div>
  );
}
