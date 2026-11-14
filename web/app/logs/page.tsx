"use client";

import React from "react";
import { EvidenceLog } from "../../components/EvidenceLog";

export default function LogsPage() {
  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <div className="kicker">Forensic Telemetry Store</div>
        <h1 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text)" }}>
          Evidence Log
        </h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Inspect all raw events in arrival sequence, examine rule score deviations, and filter by chain inclusion.
        </p>
      </div>

      <EvidenceLog />
    </div>
  );
}
