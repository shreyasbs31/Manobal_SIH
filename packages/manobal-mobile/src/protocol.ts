export const MAX_PACKETS = 500;
export const ALLOWED_KINDS = ["bio", "voice", "checkin"] as const;

export type CaptureKind = (typeof ALLOWED_KINDS)[number];

export type CaptureItem = {
  kind: CaptureKind;
  observed_at?: string;
  observed_on?: string;
  metric_code?: string;
  value?: number;
  features?: Record<string, number>;
  embedding?: number[];
  mood?: number;
  sleep_quality?: number;
  stress?: number;
  connection?: number;
};

export type CaptureBatch = {
  subject_token: string;
  client_batch_id: string;
  items: CaptureItem[];
};

const FORBIDDEN = ["service_no", "full_name", "mobile_e164", "name", "aadhaar", "rank_code"];

export function validateBatch(batch: CaptureBatch): string | null {
  if (!batch.subject_token || !batch.client_batch_id) {
    return "subject_token and client_batch_id are required";
  }
  if (!batch.items.length) {
    return "items must be a non-empty list";
  }
  if (batch.items.length > MAX_PACKETS) {
    return "batch exceeds the capture packet ceiling";
  }
  for (const item of batch.items) {
    if (FORBIDDEN.some((key) => key in item)) {
      return "identifying fields are not permitted on the device";
    }
    if (!ALLOWED_KINDS.includes(item.kind)) {
      return "unknown capture kind";
    }
  }
  return null;
}

export function buildCheckin(input: {
  subject_token: string;
  client_batch_id: string;
  mood: number;
  sleep_quality: number;
  stress: number;
  connection: number;
}): CaptureBatch {
  return {
    subject_token: input.subject_token,
    client_batch_id: input.client_batch_id,
    items: [
      {
        kind: "checkin",
        mood: input.mood,
        sleep_quality: input.sleep_quality,
        stress: input.stress,
        connection: input.connection,
      },
    ],
  };
}
