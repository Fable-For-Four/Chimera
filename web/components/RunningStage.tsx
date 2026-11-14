"use client";

import React, { useEffect, useState } from "react";
import { PipelineStage } from "../lib/types";

interface RunningStageProps {
  stages: PipelineStage[];
  events: number;
  onComplete: () => void;
}

export function RunningStage({ stages, events, onComplete }: RunningStageProps) {
  const [activeIdx, setActiveIdx] = useState<number>(0);

  useEffect(() => {
    if (activeIdx < stages.length) {
      const timer = setTimeout(() => {
        setActiveIdx((prev) => prev + 1);
      }, 520);
      return () => clearTimeout(timer);
    } else {
      const finishTimer = setTimeout(() => {
        onComplete();
      }, 450);
      return () => clearTimeout(finishTimer);
    }
  }, [activeIdx, stages.length, onComplete]);

  return (
    <div
      style={{
        maxWidth: "720px",
        margin: "40px auto",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      <div className="card">
        <div style={{ marginBottom: "16px" }}>
          <div className="kicker">How the case was worked</div>
          <h2 style={{ fontSize: "24px", fontWeight: 500, color: "var(--text)", marginTop: "4px" }}>
            Reconstructing Attack Across {events.toLocaleString()} Events
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Executing {stages.length} deterministic pipeline stages: temporal alignment, baselines, anomaly scoring, entity graph linking, hypothesis competition, and evidentiary report.
          </p>
        </div>

        <ul className="stages">
          {stages.map((stage, idx) => {
            const isDone = idx < activeIdx;
            const isCurrent = idx === activeIdx;
            const statusClass = isDone ? "ok" : isCurrent ? "now" : "wait";

            return (
              <li key={stage.name} className={statusClass}>
                <span className="dot">{isDone ? "✓" : ""}</span>
                <b>{stage.name}</b>
                <span className="res">
                  {isDone && <strong>{stage.result}</strong>}
                  <span>{stage.does}</span>
                </span>
                <span className="ms">{isDone ? `${stage.seconds}s` : ""}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
