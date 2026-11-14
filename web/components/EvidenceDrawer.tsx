"use client";

import React from "react";
import { useApp } from "../lib/state";

export function EvidenceDrawer() {
  const { caseData, selectedStep, setSelectedStep } = useApp();

  if (!caseData || !caseData.chain || !caseData.chain[selectedStep]) {
    return (
      <div className="card" style={{ padding: "20px" }}>
        <p className="kicker">No step selected</p>
      </div>
    );
  }

  const step = caseData.chain[selectedStep];
  const totalSteps = caseData.chain.length;
  const isConfident = step.confidence >= 80;

  return (
    <div className="card" style={{ gap: "16px" }}>
      {/* Header */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
          <span className="kicker" style={{ color: "var(--lime)" }}>
            Step {step.step} of {totalSteps}, {step.stage.toLowerCase()}
          </span>
          <span
            style={{
              padding: "2px 6px",
              border: "1px solid var(--border-light)",
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              color: "var(--text-muted)",
            }}
          >
            {step.technique}
          </span>
        </div>

        <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text)" }}>{step.what}</h2>

        {/* Confidence bar */}
        <div style={{ marginTop: "10px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
            <span className="mono" style={{ color: "var(--text-muted)" }}>
              {step.time} UTC ({step.minute} min into window)
            </span>
            <span className="mono" style={{ color: isConfident ? "var(--lime)" : "var(--amber)", fontWeight: 600 }}>
              {step.confidence}% sure
            </span>
          </div>
          <div style={{ height: "4px", background: "var(--panel-raised)", overflow: "hidden" }}>
            <div
              style={{
                width: `${step.confidence}%`,
                height: "100%",
                background: isConfident ? "var(--lime)" : "var(--amber)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Baseline vs Observed Deviation */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1px",
          background: "var(--border)",
          border: "1px solid var(--border)",
          overflow: "hidden",
        }}
      >
        <div style={{ background: "var(--panel-raised)", padding: "10px 12px" }}>
          <span className="kicker" style={{ display: "block", marginBottom: "2px" }}>
            Usual, over 30 days
          </span>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{step.usual}</div>
        </div>
        <div style={{ background: "var(--panel-raised)", padding: "10px 12px" }}>
          <span className="kicker" style={{ display: "block", marginBottom: "2px", color: "var(--amber)" }}>
            What happened instead
          </span>
          <div style={{ fontSize: "12px", color: "var(--text)", fontWeight: 500 }}>{step.now}</div>
        </div>
      </div>

      {/* Scoring Signals */}
      <div>
        <div className="kicker" style={{ marginBottom: "8px" }}>
          Why it scored ({step.signals.length} signals)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {step.signals.map((sig, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: "12px",
                padding: "4px 0",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <span style={{ color: "var(--text)" }}>{sig.name}</span>
              <span
                className="mono"
                style={{
                  color: sig.weight > 0 ? "var(--lime)" : "var(--amber)",
                  fontWeight: 600,
                  fontSize: "11px",
                }}
              >
                {sig.weight > 0 ? `+${sig.weight.toFixed(2)}` : sig.weight.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Exhibits (Log Lines) */}
      <div>
        <div className="kicker" style={{ marginBottom: "8px" }}>
          Log lines ({step.exhibits.length})
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {step.exhibits.map((ex, i) => {
            const letter = String.fromCharCode(65 + i);

            return (
              <div
                key={ex.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "20px minmax(0, 1fr)",
                  gap: "8px",
                  alignItems: "flex-start",
                }}
              >
                <span
                  style={{
                    width: "20px",
                    height: "20px",
                    background: "var(--lime-soft)",
                    color: "var(--lime)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    display: "grid",
                    placeItems: "center",
                    fontWeight: 700,
                  }}
                >
                  {letter}
                </span>

                <div
                  style={{
                    background: "var(--panel-raised)",
                    padding: "8px 10px",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div
                    className="mono"
                    style={{
                      fontSize: "11px",
                      color: !ex.present ? "var(--text-dim)" : "var(--text)",
                      textDecoration: !ex.present ? "line-through" : undefined,
                      opacity: !ex.present ? 0.5 : 1,
                      wordBreak: "break-all",
                    }}
                  >
                    <strong style={{ color: !ex.present ? "var(--text-dim)" : "var(--lime)", marginRight: "6px" }}>
                      {ex.id}
                    </strong>
                    {ex.raw}
                  </div>

                  <div style={{ display: "flex", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
                    {ex.late && (
                      <span className="pill pill-amber" style={{ fontSize: "9px", padding: "1px 5px" }}>
                        Arrived late, sorted by its own time
                      </span>
                    )}
                    {!ex.present && (
                      <span className="pill pill-red" style={{ fontSize: "9px", padding: "1px 5px" }}>
                        Deleted in stress test
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Navigation Buttons */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "auto", paddingTop: "10px" }}>
        <button
          className="btn btn-small"
          onClick={() => setSelectedStep(Math.max(0, selectedStep - 1))}
          disabled={selectedStep === 0}
        >
          Previous step
        </button>
        <button
          className="btn btn-small"
          onClick={() => setSelectedStep(Math.min(totalSteps - 1, selectedStep + 1))}
          disabled={selectedStep === totalSteps - 1}
        >
          Next step
        </button>
      </div>
    </div>
  );
}
