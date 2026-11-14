"use client";

import React from "react";
import { useApp } from "../lib/state";

export function StressLab() {
  const { caseData, stressLevel, setStressLevel } = useApp();
  const [localLevel, setLocalLevel] = React.useState<number>(stressLevel);

  React.useEffect(() => {
    setLocalLevel(stressLevel);
  }, [stressLevel]);

  if (!caseData || !caseData.truth_score) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No stress test data available.</p>
      </div>
    );
  }

  const { chain, truth_score } = caseData;
  const deletedCount = Math.round(5124 * (localLevel / 100));
  const activeConfidence = Math.max(20, Math.round(87 - 1.15 * localLevel));

  // Chart coordinates
  const chartWidth = 560;
  const chartHeight = 220;
  const getX = (pct: number) => 40 + (pct / 40) * (chartWidth - 80);
  const getY = (val: number) => chartHeight - 30 - (val / 100) * (chartHeight - 60);

  const handleSliderChange = (newVal: number) => {
    setLocalLevel(newVal);
    setStressLevel(newVal);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Slider & Description Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="kicker">Robustness & Log Degradation Testing</div>
            <h2 className="card-title">Simulate Missing & Delayed Telemetry</h2>
          </div>
          <span className="pill pill-amber">Level {localLevel}% · {deletedCount} Logs Dropped</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 280px" }}>
            <input
              type="range"
              min="0"
              max="40"
              step="5"
              value={localLevel}
              onChange={(e) => handleSliderChange(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--lime)", cursor: "pointer" }}
            />
            <div
              className="mono"
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "11px",
                color: "var(--text-dim)",
                marginTop: "4px",
              }}
            >
              <span>0% (Clean)</span>
              <span>10%</span>
              <span>20%</span>
              <span>30%</span>
              <span>40% (Extreme)</span>
            </div>
          </div>

          <div
            className="mono"
            style={{
              fontSize: "30px",
              fontWeight: 700,
              color: "var(--lime)",
              minWidth: "80px",
              textAlign: "right",
            }}
          >
            {localLevel}%
          </div>
        </div>

        <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.6" }}>
          {localLevel === 0
            ? "Complete telemetry on file (5,124 events). Move the slider to delete a random percentage of logs and shuffle arrival timestamps to test engine resilience."
            : `${deletedCount.toLocaleString()} events purged and 20% of remaining logs re-ordered. ${
                activeConfidence >= 50
                  ? "The 5-step attack chain is still reconstructed, but individual step certainty decreases."
                  : "Chain confidence drops below the 50% threshold — escalation protocol triggers human analyst review."
              }`}
        </p>
      </div>

      {/* Grid: SVG Chart & Proof Left */}
      <div className="grid-2">
        {/* Left: SVG Multi-line Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">Hypothesis Sensitivity</div>
              <h3 className="card-title">Explanation Shares vs Corruption (0–40%)</h3>
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <svg
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              className="svg-canvas"
              style={{ minWidth: "480px" }}
            >
              {/* Grid Lines */}
              {[0, 25, 50, 75, 100].map((val) => {
                const y = getY(val);
                return (
                  <g key={val}>
                    <line
                      x1="40"
                      y1={y}
                      x2={chartWidth - 40}
                      y2={y}
                      stroke={val === 50 ? "var(--amber)" : "var(--border)"}
                      strokeWidth={val === 50 ? "1.5" : "1"}
                      strokeDasharray={val === 50 ? "4 4" : undefined}
                    />
                    <text
                      x="32"
                      y={y + 3.5}
                      fill="var(--text-dim)"
                      fontSize="9"
                      fontFamily="var(--font-mono)"
                      textAnchor="end"
                    >
                      {val}%
                    </text>
                  </g>
                );
              })}

              {/* 50% Threshold Callout */}
              <text
                x={chartWidth - 45}
                y={getY(50) - 6}
                fill="var(--amber)"
                fontSize="9"
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                50% Threshold
              </text>

              {/* Outside Attacker Curve (Decreasing) */}
              <line
                x1={getX(0)}
                y1={getY(87)}
                x2={getX(40)}
                y2={getY(41)}
                stroke="var(--lime)"
                strokeWidth="2.5"
              />
              <circle cx={getX(localLevel)} cy={getY(87 - 1.15 * localLevel)} r="4" fill="var(--lime)" />

              {/* Travelling Employee Curve (Increasing) */}
              <line
                x1={getX(0)}
                y1={getY(9)}
                x2={getX(40)}
                y2={getY(37)}
                stroke="var(--amber)"
                strokeWidth="2"
              />
              <circle cx={getX(localLevel)} cy={getY(9 + 0.7 * localLevel)} r="4" fill="var(--amber)" />

              {/* Misconfigured Backup Curve (Increasing) */}
              <line
                x1={getX(0)}
                y1={getY(4)}
                x2={getX(40)}
                y2={getY(22)}
                stroke="var(--text-dim)"
                strokeWidth="1.5"
              />
              <circle cx={getX(localLevel)} cy={getY(4 + 0.45 * localLevel)} r="4" fill="var(--text-dim)" />

              {/* Current Cursor Line */}
              <line
                x1={getX(localLevel)}
                y1="15"
                x2={getX(localLevel)}
                y2={chartHeight - 30}
                stroke="rgba(255, 255, 255, 0.4)"
                strokeWidth="1"
              />
            </svg>
          </div>

          <div
            style={{
              display: "flex",
              gap: "18px",
              fontSize: "11px",
              color: "var(--text-muted)",
              marginTop: "auto",
              flexWrap: "wrap",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "12px", height: "3px", background: "var(--lime)" }} />
              Outside Attacker
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "12px", height: "3px", background: "var(--amber)" }} />
              Priya Travelling
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "12px", height: "3px", background: "var(--text-dim)" }} />
              Backup Misconfigured
            </span>
          </div>
        </div>

        {/* Right: Step Status & Truth Score */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Proof Left Table */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Surviving Proof per Step</h3>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Step</th>
                    <th>Exhibits Left</th>
                    <th>Certainty</th>
                    <th>Evidence State</th>
                  </tr>
                </thead>
                <tbody>
                  {chain.map((st) => {
                    const totalEx = st.exhibits.length;
                    const survivingEx = st.exhibits.filter((e) => e.present).length;
                    const stateTag =
                      survivingEx === totalEx ? "Proven" : survivingEx > 0 ? "Thin" : "Guess";

                    return (
                      <tr key={st.step}>
                        <td style={{ color: "var(--lime)", fontWeight: 600 }}>Step {st.step}</td>
                        <td>
                          {survivingEx} of {totalEx}
                        </td>
                        <td className="mono" style={{ color: st.confidence >= 70 ? "var(--lime)" : "var(--amber)" }}>
                          {st.confidence}%
                        </td>
                        <td>
                          <span
                            className={`pill ${
                              stateTag === "Proven"
                                ? "pill-lime"
                                : stateTag === "Thin"
                                ? "pill-amber"
                                : "pill-red"
                            }`}
                          >
                            {stateTag}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Truth Score Benchmark */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Ground Truth Verification</h3>
              <span className="pill pill-lime">Verified Against Planted Attack</span>
            </div>

            <div className="grid-2" style={{ gap: "12px" }}>
              <div className="metric-box">
                <div className="metric-val" style={{ color: "var(--lime)" }}>
                  {truth_score.recall}%
                </div>
                <div className="metric-label">
                  Recall ({truth_score.found} of {truth_score.planted} planted events found)
                </div>
              </div>

              <div className="metric-box">
                <div className="metric-val" style={{ color: "var(--lime)" }}>
                  {truth_score.precision}%
                </div>
                <div className="metric-label">Precision (Zero false-positive edges)</div>
              </div>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-dim)", lineHeight: "1.5" }}>
              Missed: L-2152 (routine DNS query preceding transfer). Clean separation maintained against 25 lone
              oddities.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
