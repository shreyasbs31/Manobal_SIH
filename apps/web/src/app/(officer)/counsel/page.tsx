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
      label: label.slice(6) || tx.freeSlot,
      request_id: null,
    }));
  }, [data, tx]);
  const active =
    data?.requests.find((item) => String(item.id) === picked) ?? data?.requests[0];
  const activeId = active ? String(active.id) : "";
  const activeAnonymous = String(active?.kind) === "anonymous";
  const activeHindi = String(active?.language) === "hi";
  const activeSummary =
    activeId === "req-hi-1" ? tx.counselLeaveSummary : tx.counselPrivateSummary;
  const activePrivacy = activeAnonymous ? tx.counselNameHidden : tx.counselNameShared;
  const activeReference = activeAnonymous
    ? String(active?.reference ?? active?.handle ?? "River-17")
    : String(active?.reference ?? "CS-1042");

  async function run(work: () => Promise<void>) {
    setBusy(true);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
        setStatus(caught instanceof Error ? caught.message : tx.couldNotComplete);
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScreenState
      error={error}
      loading={loading}
      offline={offline}
      empty={!data}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
      {data ? (
        <div className="mb-desk mb-counsel">
          <p className="mb-desk-purpose">{tx.counselPurpose}</p>
          <section className="mb-sheet">
            <div className="mb-section-head">
              <div>
                <h2>{tx.today}</h2>
                <p>{tx.counselSelect}</p>
              </div>
            </div>
            <div className="mb-slot-grid">
              {slots.map((slot) => {
                const request = data.requests.find((item) => String(item.id) === slot.request_id);
                const hindi = String(request?.language) === "hi";
                const anonymous = String(request?.kind) === "anonymous";
                return (
                  <button
                    aria-pressed={slotId === slot.id}
                    className="mb-slot"
                    data-state={slot.request_id ? "held" : "free"}
                    key={slot.id}
                    onClick={() => {
                      setSlotId(slot.id);
                      if (slot.request_id) setPicked(slot.request_id);
                    }}
                    type="button"
                  >
                    <strong>{slot.when}</strong>
                    <span>{slot.request_id ? tx.counselReserved : tx.counselAvailable}</span>
                    {slot.request_id ? (
                      <em>
                        {hindi ? tx.counselHindi : tx.counselEnglish}
                        {" · "}
                        {anonymous ? tx.counselNameHidden : tx.counselNameShared}
                      </em>
                    ) : null}
                  </button>
                );
              })}
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
                    {String(item.id) === "req-hi-1" ? tx.counselLeaveSummary : tx.counselPrivateSummary}
                  </strong>
                  <span>{String(item.kind) === "anonymous" ? tx.counselNameHidden : tx.counselNameShared}</span>
                  <span>{String(item.language) === "hi" ? tx.counselHindi : tx.counselEnglish}</span>
                  <em>{tx.counselQueued}</em>
                </button>
              ))}
            </div>
          </section>
          {active ? (
            <section className="mb-counsel-session">
              <div className="mb-sheet mb-counsel-brief">
                <div className="mb-section-head">
                  <div>
                    <h2>{tx.counselSession}</h2>
                    <p>{activeSummary}</p>
                  </div>
                  <span className="mb-status-pill" data-status="open">{tx.counselQueued}</span>
                </div>
                <dl className="mb-fact-list">
                  <div>
                    <dt>{tx.counselPrivacy}</dt>
                    <dd>{activePrivacy}</dd>
                  </div>
                  <div>
                    <dt>{tx.acuteLanguage}</dt>
                    <dd>{activeHindi ? tx.counselHindi : tx.counselEnglish}</dd>
                  </div>
                  <div>
                    <dt>{tx.counselPrivateRef}</dt>
                    <dd>{activeReference}</dd>
                  </div>
                  <div>
                    <dt>{tx.counselMatched}</dt>
                    <dd>{tx.counselNoNotes}</dd>
                  </div>
                </dl>
              </div>
              <CallPanel
                joinLabel={tx.joinCall}
                leaveLabel={tx.leaveCall}
                onJoin={() => {
                  void engineClient()
                    .callsToken()
                    .then((result) => {
                      setStatus(result.configured ? tx.callReady : tx.callUnavailable);
                    });
                }}
                peer={activeAnonymous ? `${tx.counselPrivateRef} ${activeReference}` : tx.counselNameShared}
                status={status || tx.counselPrepare}
              />
              <div className="mb-sheet mb-counsel-notes">
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
                          setStatus(tx.booked);
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
                        setStatus(tx.noteSaved);
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
                          tx.restReason,
                        );
                        setStatus(tx.suggestedRestDone);
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
