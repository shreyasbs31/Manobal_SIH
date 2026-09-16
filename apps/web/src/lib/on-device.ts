export async function onDeviceCapability(): Promise<{
  available: boolean;
  reason: string;
}> {
  if (typeof navigator === "undefined") {
    return { available: false, reason: "server" };
  }
  const gpu = (navigator as Navigator & { gpu?: { requestAdapter: () => Promise<unknown> } }).gpu;
  if (!gpu) {
    return { available: false, reason: "no-webgpu" };
  }
  try {
    const adapter = await gpu.requestAdapter();
    if (!adapter) {
      return { available: false, reason: "no-adapter" };
    }
    return { available: true, reason: "webgpu" };
  } catch {
    return { available: false, reason: "webgpu-error" };
  }
}

export const ON_DEVICE_LABEL = "On-device preview";
export const ON_DEVICE_HINDI_NOTE =
  "On-device preview is English only. Use the structured check-in while offline.";

const BLOCKED = ["tablet i should take", "clinical label", "what condition do i have"];

export function localOutputGuard(text: string): boolean {
  const blob = text.toLowerCase();
  return BLOCKED.some((item) => blob.includes(item));
}

export function localReflect(text: string, lang: string): string {
  if (!lang.startsWith("en")) {
    return ON_DEVICE_HINDI_NOTE;
  }
  if (localOutputGuard(text)) {
    return "I can stay with how this feels. A person can help with anything medical.";
  }
  return `I hear that this is sitting with you. What part of that feels heaviest right now? (${text.slice(0, 40)})`;
}
