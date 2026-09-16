import { EmptyState, PublicHeader } from "@manobal/ui";
import Link from "next/link";

import { manobalMode } from "@/lib/mode";

export default function NotFound() {
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-login">
        <h1>This route is not available</h1>
        <EmptyState
          message="Return to the MANOBAL landing page."
          title="No matching view"
        />
        <Link className="mb-primary" href="/">
          Return home
        </Link>
      </main>
    </div>
  );
}
