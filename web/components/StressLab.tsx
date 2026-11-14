"use client";

import React from "react";
import { getStressCase } from "../lib/api";
import { useApp } from "../lib/state";

const LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40];
const LINE_COLORS = ["var(--lime)", "var(--amber)", "var(--text-dim)"];
const LINE_WIDTHS = ["2.5", "2", "1.5"];

interface LevelShares {
  level: number;
  shares: number[];
}

export function StressLab() {
  const { caseData, stressLevel, setStressLevel } = useApp();
  const [localLevel, setLocalLevel] = React.useState<number>(stressLevel);
  const [series, setSeries] = React.useState<LevelShares[]>([]);

  React.useEffect(() => {
    setLocalLevel(stressLevel);
  }, [stressLevel]);

  React.useEffect(() => {
    let mounted = true;
    Promise.allSettled(LEVELS.map((level) => getStressCase(level))).then((results) => {
      if (!mounted) return;
      const points: LevelShares[] = [];
      results.forEach((result, i) => {
        if (result.status === "fulfilled") {
          points.push({ level: LEVELS[i], shares: result.value.hypotheses.map((h) => h.share) });
        }
      });
      setSeries(points);
    });
    return () => {
      mounted = false;
    };
  }, []);

  if (!caseData || !caseData.truth_score) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No stress test data available.</p>
      </div>
    );
  }

  const { chain, truth_score, hypotheses, verdict, summary } = caseData;
  const deletedCount = caseData.deleted;
  const shownLevel = caseData.level;

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
          <span className="pill pill-amber">
            Level {shownLevel}% · {deletedCount.toLocaleString()} Logs Dropped
          </span>
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
          {shownLevel === 0
            ? `Complete telemetry on file (${summary.events.toLocaleString()} events). Move the slider to delete a random percentage of logs and shuffle arrival timestamps to test engine resilience.`
            : `${deletedCount.toLocaleString()} events purged and 20% of remaining logs re-ordered. ${
                !verdict.found
                  ? "No attack chain could be rebuilt from what is left."
                  : verdict.confidence >= 50
                  ? `The ${chain.length}-step attack chain is still reconstructed at ${verdict.confidence}% confidence.`
                  : `Chain confidence drops to ${verdict.confidence}%, below the 50% threshold. A human analyst should review it.`
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

              {hypotheses.map((hyp, idx) => (
                <g key={hyp.name}>
                  <polyline
                    points={series
                      .filter((p) => p.shares[idx] !== undefined)
                      .map((p) => `${getX(p.level)},${getY(p.shares[idx])}`)
                      .join(" ")}
                    fill="none"
                    stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                    strokeWidth={LINE_WIDTHS[idx % LINE_WIDTHS.length]}
                  />
                  <circle
                    cx={getX(shownLevel)}
                    cy={getY(hyp.share)}
                    r="4"
                    fill={LINE_COLORS[idx % LINE_COLORS.length]}
                  />
                </g>
              ))}

              <line
                x1={getX(shownLevel)}
                y1="15"
                x2={getX(shownLevel)}
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
            {hypotheses.map((hyp, idx) => (
              <span key={hyp.name} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span
                  style={{ width: "12px", height: "3px", background: LINE_COLORS[idx % LINE_COLORS.length] }}
                />
                {hyp.name} ({hyp.share}%)
              </span>
            ))}
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
                <div className="metric-label">
                  Precision ({truth_score.false_links.length} false links)
                </div>
              </div>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-dim)", lineHeight: "1.5" }}>
              {truth_score.missed.length > 0
                ? `Missed: ${truth_score.missed.join(", ")}.`
                : "No planted event was missed."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
