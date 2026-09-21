"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type ErrorEnvelope = {
  error?: {
    message?: string;
    hint?: string;
  };
};

export function AccessForm({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState("Enter the code shared with you.");

  async function continueToDemo() {
    setPending(true);
    setStatus("Checking access.");
    try {
      const response = await fetch("/api/v1/auth/demo-access", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as ErrorEnvelope;
        throw new Error(
          [payload.error?.message, payload.error?.hint].filter(Boolean).join(" "),
        );
      }
      router.replace(nextPath);
      router.refresh();
    } catch (error: unknown) {
      setStatus(
        error instanceof Error && error.message
          ? error.message
          : "Access could not be checked. Try again.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form
      className="mb-home-stack"
      onSubmit={(event) => {
        event.preventDefault();
        void continueToDemo();
      }}
    >
      <label>
        Access code
        <input
          autoComplete="current-password"
          autoFocus
          minLength={8}
          onChange={(event) => setCode(event.target.value)}
          required
          type="password"
          value={code}
        />
      </label>
      <button
        className="mb-primary"
        disabled={pending || code.length < 8}
        type="submit"
      >
        {pending ? "Checking access" : "Continue to MANOBAL"}
      </button>
      <p className="form-status" role="status">
        {status}
      </p>
    </form>
  );
}
