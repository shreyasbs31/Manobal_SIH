export function RibbonMark({ title = "Baseline ribbon" }: { title?: string }) {
  return (
    <svg
      className="mb-ribbon-mark"
      viewBox="0 0 54 28"
      role="img"
      aria-label={title}
    >
      <path d="M2 16 C12 6 20 7 28 14 S42 24 52 11" />
      <path d="M2 22 C12 12 20 13 28 20 S42 30 52 17" />
    </svg>
  );
}

export function SyntheticMarker() {
  return <span className="mb-chip mb-chip--synthetic">Synthetic data</span>;
}
