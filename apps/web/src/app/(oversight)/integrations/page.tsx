import { EmptyState } from "@manobal/ui";

export default function IntegrationsPage() {
  return (
    <EmptyState
      message="CSV and API uploads are tokenised before they reach the engine."
      title="No connector runs yet"
    />
  );
}
