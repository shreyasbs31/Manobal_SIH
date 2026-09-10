import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { PairedDevice, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { formatWhen } from "../ui/format";

type Props = { session: Session };

export function PersonnelDevices({ session }: Props) {
  const api = createClient(session);
  const [devices, setDevices] = useState<PairedDevice[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const next = await api.devices();
    setDevices(next.devices);
    setLoaded(true);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setLoaded(true);
      setError(err instanceof ApiError ? err.message : "devices unavailable");
    });
  }, [session.token]);

  async function onPair(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const formEl = event.currentTarget;
    try {
      await api.pairDevice(String(form.get("device_id")), String(form.get("public_key")));
      setError("");
      formEl.reset();
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not pair this device");
    }
  }

  async function revoke(id: number) {
    try {
      await api.revokeDevice(id);
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not revoke this device");
    }
  }

  return (
    <section className="panel anchor" id="devices">
      <h2>Paired devices</h2>
      <p className="muted">The device holds a token, never a service number.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <form className="grid two" onSubmit={(event) => void onPair(event)}>
        <label htmlFor="device_id">
          Device id
          <input id="device_id" name="device_id" required aria-required="true" minLength={8} />
        </label>
        <label htmlFor="public_key">
          Public key
          <input id="public_key" name="public_key" required aria-required="true" minLength={32} />
        </label>
        <div>
          <button type="submit">Pair</button>
        </div>
      </form>
      {loaded && !devices.length ? (
        <EmptyState title="No devices paired">Pair a handset so check-ins can arrive without a service number.</EmptyState>
      ) : (
        <ul>
          {devices.map((row) => (
            <li key={row.id}>
              {row.device_id} {row.revoked_at ? `(revoked ${formatWhen(row.revoked_at)})` : ""}
              {row.revoked_at ? null : (
                <button type="button" className="ghost" onClick={() => void revoke(row.id)}>
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
