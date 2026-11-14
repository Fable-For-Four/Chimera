"use client";

import React from "react";
import { EvidenceLog } from "../../components/EvidenceLog";

export default function LogsPage() {
  return (
    <div>
      <header className="page-head">
        <h1>Evidence log</h1>
        <p>Every event the engine read, with its score and the chain step it belongs to.</p>
      </header>

      <EvidenceLog />
    </div>
  );
}
