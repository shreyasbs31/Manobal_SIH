import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { PairedDevice, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function PersonnelDevices({ session }: Props) {
  const api = createClient(session);
  const [devices, setDevices] = useState<PairedDevice[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    const next = await api.devices();
    setDevices(next.devices);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "devices unavailable");
    });
  }, [session.token]);

  async function onPair(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.pairDevice(String(form.get("device_id")), String(form.get("public_key")));
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not pair this device");
    }
  }

  return (
    <section className="panel">
      <h2>Paired devices</h2>
      <p className="muted">The device holds a token, never a service number.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <form className="grid" onSubmit={(event) => void onPair(event)}>
        <label htmlFor="device_id">
          Device id
          <input id="device_id" name="device_id" required aria-required="true" minLength={8} />
        </label>
        <label htmlFor="public_key">
          Public key
          <input id="public_key" name="public_key" required aria-required="true" minLength={32} />
        </label>
        <button type="submit">Pair</button>
      </form>
      <ul>
        {devices.map((row) => (
          <li key={row.id}>
            {row.device_id} {row.revoked_at ? "(revoked)" : ""}
            {row.revoked_at ? null : (
              <button type="button" className="ghost" onClick={() => void api.revokeDevice(row.id).then(refresh)}>
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
