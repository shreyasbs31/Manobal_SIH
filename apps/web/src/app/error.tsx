"use client";

import { ErrorState, PublicHeader } from "@manobal/ui";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader />
      <main className="mb-login">
        <h1>This view needs another try</h1>
        <p>No data was changed.</p>
        <ErrorState retry={reset} />
      </main>
    </div>
  );
}
