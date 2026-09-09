import { type CaptureBatch, validateBatch } from "./protocol";

export type SyncResult = {
  accepted: boolean;
  status: number;
  body: Record<string, unknown>;
};

export async function syncBatch(
  batch: CaptureBatch,
  options: { edgeUrl: string; token: string; fetchImpl?: typeof fetch },
): Promise<SyncResult> {
  const { edgeUrl, token, fetchImpl = fetch } = options;
  const reason = validateBatch(batch);
  if (reason) {
    return { accepted: false, status: 422, body: { code: "MB-4220", detail: reason } };
  }
  const response = await fetchImpl(`${edgeUrl.replace(/\/$/, "")}/v1/sync`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(batch),
  });
  const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  return { accepted: response.ok, status: response.status, body };
}
