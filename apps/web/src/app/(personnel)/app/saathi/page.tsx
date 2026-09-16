import { AudioClearedChip, CaptionStream, VoiceOrb } from "@manobal/ui";

export default function SaathiCompanionPage() {
  return (
    <div className="mb-home-stack">
      <h1>Saathi</h1>
      <p>What you say here stays in this session unless you save it as a private journal.</p>
      <VoiceOrb state="listening" />
      <CaptionStream
        language="Hindi"
        lines={[
          "Aap kaise hain aaj?",
          "You have been on duty 11 days in a row. A short recovery routine can help.",
        ]}
      />
      <AudioClearedChip />
      <div className="mb-action-row">
        <button className="mb-primary" type="button">
          Check in
        </button>
        <button className="mb-secondary" type="button">
          Ask
        </button>
        <button className="mb-secondary" type="button">
          Talk it through
        </button>
      </div>
    </div>
  );
}
