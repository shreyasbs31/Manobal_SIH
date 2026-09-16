export function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 0) {
    return 0;
  }
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

export function ribbonStats(values) {
  const series = values.map((point) => point.value);
  const centre = median(series);
  const spread = 1.4826 * Math.max(
    median(series.map((value) => Math.abs(value - centre))),
    0.2,
  );
  return { centre, spread };
}
