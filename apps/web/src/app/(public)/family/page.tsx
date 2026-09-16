"use client";

import { useState } from "react";

export default function FamilyPublicPage() {
  const [sent, setSent] = useState(false);
  return (
    <main className="mb-home-stack" style={{ padding: 24, maxWidth: 480, marginInline: "auto" }}>
      <h1 className="mb-type-title">Family connect</h1>
      <p>This page has no personal data. It is safe to share.</p>
      <ul>
        <li>How to support someone far away</li>
        <li>Tele-MANAS 14416</li>
        <li>Force family welfare contacts</li>
      </ul>
      <p>
        A family member can reach the sector counsellor without creating a flag. The person is
        asked first if they want that conversation.
      </p>
      <button className="mb-primary" onClick={() => setSent(true)} type="button">
        {sent ? "Counsellor will reach out if the person agrees" : "Family concern line"}
      </button>
    </main>
  );
}
