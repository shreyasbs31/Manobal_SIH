"use client";

import { CallPanel, EmptyState } from "@manobal/ui";
import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Slot = { id: string; when: string; label: string; request_id: string | null };

export default function CounselPage() {
  const { tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine("counsel-desk", (client, signal) =>
    client.counselDesk(signal),
  );
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const [picked, setPicked] = useState("");
  const [slotId, setSlotId] = useState("");
  const [busy, setBusy] = useState(false);
  const slots: Slot[] = useMemo(() => {
    if (data?.slots?.length) {
      return data.slots;
    }
    return (data?.calendar ?? []).map((label, index) => ({
      id: `slot-${index}`,
      when: label.slice(0, 5),
      label: label.slice(6) || "Free",
      request_id: null,
    }));
  }, [data]);
  const active =
    data?.requests.find((item) => String(item.id) === picked) ?? data?.requests[0];

  async function run(work: () => Promise<void>) {
    setBusy(true);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setStatus(caught instanceof Error ? caught.message : "Could not complete that action.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-desk mb-counsel">
          <section className="mb-sheet">
            <h2>{tx.today}</h2>
            <div className="mb-slot-grid">
              {slots.map((slot) => (
                <button
                  aria-pressed={slotId === slot.id}
                  className="mb-slot"
                  data-state={slot.request_id ? "held" : "free"}
                  key={slot.id}
                  onClick={() => {
                    setSlotId(slot.id);
                    if (slot.request_id) {
                      setPicked(slot.request_id);
                    }
                  }}
                  type="button"
                >
                  <strong>{slot.when}</strong>
                  <span>{slot.label}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="mb-sheet">
            <h2>{tx.requests}</h2>
            <div className="mb-work-list">
              {data.requests.map((item) => (
                <button
                  aria-pressed={String(item.id) === String(active?.id)}
                  className="mb-request"
                  key={String(item.id)}
                  onClick={() => setPicked(String(item.id))}
                  type="button"
                >
                  <strong>
                    {String(item.kind) === "named" ? tx.named : tx.anonymous}{" "}
                    {String(item.language) === "hi" ? tx.langHi : tx.langEn}
                  </strong>
                  <span>
                    {item.handle ? String(item.handle) : String(item.summary)}
                  </span>
                </button>
              ))}
            </div>
          </section>
          {active ? (
            <section className="mb-counsel-session">
              <CallPanel
                joinLabel={tx.joinCall}
                onJoin={() => {
                  void engineClient()
                    .callsToken()
                    .then((result) => {
                      setStatus(result.configured ? "Call is ready." : "Call is not available right now.");
                    });
                }}
                peer={active.handle ? String(active.handle) : "Named session"}
                status={status || String(active.summary ?? "")}
              />
              <div className="mb-sheet">
                <label>
                  {tx.privateNote}
                  <textarea onChange={(event) => setNote(event.target.value)} value={note} />
                </label>
                <div className="mb-action-row">
                  {slotId ? (
                    <button
                      className="mb-secondary"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          await engineClient().counselBook(slotId, String(active.id));
                          setStatus(`Booked ${slotId.replace("slot-", "")}.`);
                        })
                      }
                      type="button"
                    >
                      {tx.bookSlot}
                    </button>
                  ) : null}
                  <button
                    className="mb-secondary"
                    disabled={busy || !note.trim()}
                    onClick={() =>
                      void run(async () => {
                        await engineClient().counselNotes(
                          String(active.id),
                          note,
                        );
                        setStatus("Note saved.");
                      })
                    }
                    type="button"
                  >
                    {tx.saveNote}
                  </button>
                  <button
                    className="mb-primary"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await engineClient().counselSuggest(
                          "MB-4091",
                          "REST_48H",
                          "A rest cycle may help.",
                        );
                        setStatus("Suggested 48-hour rest.");
                      })
                    }
                    type="button"
                  >
                    {tx.suggestRest}
                  </button>
                </div>
              </div>
            </section>
          ) : (
            <EmptyState message={tx.pickRequest} title={tx.noSession} />
          )}
        </div>
      ) : null}
    </ScreenState>
  );
}
