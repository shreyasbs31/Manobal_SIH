"use client";

import { useState } from "react";

import { engineClient } from "@/lib/engine";
import { drainQueue } from "@/lib/offline";
import { announceWorld } from "@/lib/world";

export function DirectorControls() {
  const [edge, setEdge] = useState("up");
  const [air, setAir] = useState(
    typeof window === "undefined" ? false : window.localStorage.getItem("manobal.airplane") === "1",
  );
  const [drain, setDrain] = useState(0);

  return (
    <div className="mb-action-row">
      <button className="mb-secondary" type="button">
        Pause
      </button>
      <button className="mb-secondary" type="button">
        +1 day
      </button>
      <button className="mb-secondary" type="button">
        +1 week
      </button>
      <button className="mb-primary" type="button">
        Run nightly scoring now
      </button>
      <button
        aria-pressed={air}
        className="mb-secondary"
        onClick={() => {
          const next = !air;
          setAir(next);
          window.localStorage.setItem("manobal.airplane", next ? "1" : "0");
          window.dispatchEvent(new Event("manobal-airplane"));
          announceWorld("airplane");
        }}
        type="button"
      >
        {air ? "Airplane on" : "Airplane off"}
      </button>
      <button
        className="mb-secondary"
        onClick={() => {
          const up = edge !== "up";
          void engineClient()
            .setEdgeLink(up)
            .then((result) => {
              setEdge(result.up ? "up" : "down");
            });
        }}
        type="button"
      >
        Unit server link: {edge}
      </button>
      <button
        className="mb-secondary"
        onClick={() => {
          void drainQueue(async (kind, payload, id) => {
            await engineClient().syncQueue([
              { kind, payload: payload as Record<string, unknown>, client_id: id },
            ]);
          }).then(setDrain);
        }}
        type="button"
      >
        Drain queue {drain ? `(${drain})` : ""}
      </button>
    </div>
  );
}
