export function isDemoMode(): boolean {
  return (process.env.NEXT_PUBLIC_MANOBAL_MODE ?? "demo") === "demo";
}

export function manobalMode(): "demo" | "sovereign" {
  return isDemoMode() ? "demo" : "sovereign";
}
