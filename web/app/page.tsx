"use client";

import React from "react";
import { useApp } from "../lib/state";
import { Start } from "../components/Start";
import { Overview } from "../components/Overview";
import { RunningStage } from "../components/RunningStage";

export default function HomePage() {
  const { isRunning, caseData, finishInvestigation } = useApp();

  if (isRunning) {
    return (
      <RunningStage
        stages={caseData?.stages || [
          { name: "Sort", does: "Put every event in true time order", result: "212 late events moved", seconds: 0.4 },
          { name: "Profile", does: "Learn what is normal for each user and machine", result: "70 baselines from 30 days", seconds: 1.1 },
          { name: "Score", does: "Mark events that break their baseline", result: "37 weak signals", seconds: 0.6 },
          { name: "Link", does: "Join signals that share a user or machine", result: "1 chain, 5 steps, 11 events", seconds: 0.3 },
          { name: "Challenge", does: "Try innocent explanations against the chain", result: "2 tested, both weaker", seconds: 0.5 },
          { name: "Report", does: "Write the verdict with a log line for every claim", result: "5 claims, 5 citations", seconds: 2.2 },
        ]}
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
