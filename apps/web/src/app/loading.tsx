import { LoadingState, PublicHeader } from "@manobal/ui";

export default function Loading() {
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader />
      <main className="mb-login">
        <LoadingState />
      </main>
    </div>
  );
}
