"use client";

import { t } from "@manobal/i18n";
import { useEffect, useState } from "react";

import { canDrainPersonnelQueue, engineClient } from "@/lib/engine";
import { drainQueue, queueCount } from "@/lib/offline";

export function OfflineObserver() {
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);

  useEffect(() => {
    const update = () => {
      const airplane = window.localStorage.getItem("manobal.airplane") === "1";
      setOffline(!window.navigator.onLine || airplane);
      void queueCount().then(setQueued);
    };
    const drain = () => {
      if (!window.navigator.onLine || window.localStorage.getItem("manobal.airplane") === "1") {
        return;
      }
      if (!canDrainPersonnelQueue()) {
        update();
        return;
      }
      void drainQueue(async (kind, payload, id) => {
        await engineClient().syncQueue([
          { kind, payload: payload as Record<string, unknown>, client_id: id },
        ]);
      }).then(update);
    };
    update();
    const onStorage = (event: StorageEvent) => {
      if (event.key === "manobal.airplane") {
        update();
      }
    };
    window.addEventListener("online", drain);
    window.addEventListener("offline", update);
    window.addEventListener("manobal-airplane", update);
    window.addEventListener("manobal-queue", update);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("online", drain);
      window.removeEventListener("offline", update);
      window.removeEventListener("manobal-airplane", update);
      window.removeEventListener("manobal-queue", update);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  if (!offline) {
    return null;
  }

  const lang =
    typeof window === "undefined" ? "en" : window.localStorage.getItem("manobal.language") ?? "en";
  return (
    <div className="offline-banner" role="status">
      {t("offline.bar", lang === "hi" || lang === "ta" ? lang : "en", { n: queued })}
    </div>
  );
}
