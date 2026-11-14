"use client";

import React from "react";
import { StressLab } from "../../components/StressLab";

export default function StressPage() {
  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <div className="kicker">Uncertainty & Adversarial Degradation</div>
        <h1 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text)" }}>
          Stress Testing Lab
        </h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Interactively purge telemetry and inject clock skew to evaluate engine reconstruction thresholds.
        </p>
      </div>

      <StressLab />
    </div>
  );
}
