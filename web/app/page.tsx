"use client";

import React from "react";
import { useApp } from "../lib/state";
import { Start } from "../components/Start";
import { Overview } from "../components/Overview";
import { RunningStage } from "../components/RunningStage";

export default function HomePage() {
  const { isRunning, caseData, finishInvestigation } = useApp();

  if (isRunning) {
    if (!caseData) {
      return (
        <div className="card" style={{ maxWidth: "720px", margin: "40px auto", textAlign: "center" }}>
          <div className="kicker">How the case was worked</div>
          <p style={{ fontSize: "15px", color: "var(--text)", marginTop: "8px" }}>
            Running the investigation engine…
          </p>
        </div>
      );
    }
    return (
      <RunningStage
        stages={caseData.stages}
        events={caseData.summary.events}
        onComplete={finishInvestigation}
      />
    );
  }

  const isCaseReady = Boolean(caseData && caseData.verdict && caseData.verdict.found);

  if (isCaseReady) {
    return <Overview />;
  }

  return <Start />;
}
