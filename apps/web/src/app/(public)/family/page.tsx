"use client";

import { PublicHeader } from "@manobal/ui";
import { useState } from "react";

import { manobalMode } from "@/lib/mode";

export default function FamilyPublicPage() {
  const [sent, setSent] = useState(false);
  return (
    <div className="mb-theme" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-login">
        <h1 className="mb-type-title">Family connect</h1>
        <p>This page does not include anyone's name. It is safe to share.</p>
        <ul>
          <li>How to support someone far away</li>
          <li>Tele-MANAS 14416</li>
          <li>Force family welfare contacts</li>
        </ul>
        <p>
          A family member can reach a counsellor. The person is asked first if they want that
          conversation.
        </p>
        <button className="mb-primary" onClick={() => setSent(true)} type="button">
          {sent ? "Counsellor will reach out if the person agrees" : "Family concern line"}
        </button>
      </main>
    </div>
  );
}
