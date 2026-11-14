"use client";

import React from "react";
import Link from "next/link";
import { useApp } from "../lib/state";

export function Start() {
  const { intake, user, isRunning, runInvestigation } = useApp();

  if (!intake) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">Loading intake telemetry...</p>
      </div>
    );
  }

  const { summary, alert_rules, volume, latest } = intake;
  const maxCount = Math.max(1, ...volume.map((pt) => pt.count));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Metrics Row */}
      <div className="grid-4">
        <div className="metric-box">
          <div className="metric-val">{summary.events.toLocaleString()}</div>
          <div className="metric-label">Simulated log events</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{summary.sources}</div>
          <div className="metric-label">Log sources</div>
        </div>
        <div className="metric-box">
          <div className="metric-val" style={{ color: "var(--amber)" }}>
            {summary.late}
          </div>
          <div className="metric-label">Arrived late, out of order</div>
        </div>
        <div className="metric-box">
          <div className="metric-val" style={{ color: "var(--lime)" }}>
            {summary.alerts_fired}
          </div>
          <div className="metric-label">Alerts fired</div>
        </div>
      </div>

      {/* Main Grid: Volume & Alerts */}
      <div className="grid-2">
        {/* Left: Volume & CTA */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">Events per 5 minutes</div>
              <h2 className="card-title">Event volume, 03:00 to 04:30 UTC</h2>
            </div>
            <span className="pill pill-lime">All {summary.sources} Sources Healthy</span>
          </div>

          {/* SVG Volume Bars */}
          <div className="table-container" style={{ padding: "10px 0" }}>
            <svg viewBox="0 0 760 110" className="svg-canvas" role="img" aria-label="Event volume per 5 minutes">
              {volume.map((pt, idx) => {
                const barWidth = 700 / volume.length - 4;
                const barHeight = (pt.count / maxCount) * 80;
                const x = 30 + idx * (700 / volume.length);
                const y = 85 - barHeight;

                return (
                  <g key={pt.start}>
                    <rect
                      x={x}
                      y={y}
                      width={barWidth}
                      height={barHeight}
                      rx="2"
                      fill="var(--border-light)"
                    />
                    {idx % 3 === 0 && (
                      <text
                        x={x + barWidth / 2}
                        y={102}
                        fill="var(--text-dim)"
                        fontSize="10"
                        fontFamily="var(--font-mono)"
                        textAnchor="middle"
                      >
                        {pt.start}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: "var(--panel-raised)",
              padding: "16px 20px",
              borderRadius: "6px",
              border: "1px solid var(--border)",
              marginTop: "auto",
              flexWrap: "wrap",
              gap: "14px",
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text)" }}>
                Zero alerts triggered across the whole night.
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Each attack step evaded single-event thresholds. Correlate the timeline.
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={runInvestigation}
              disabled={isRunning || user?.role === "viewer"}
            >
              {isRunning ? "Running Engine Pipeline..." : "Run Multi-Stage Investigation"}
            </button>
          </div>
        </div>

        {/* Right: Alert Rules */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">What the usual alerts saw</div>
              <h2 className="card-title">
                Alert rules ({alert_rules.filter((r) => r.fired).length} of {alert_rules.length} fired)
              </h2>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {alert_rules.map((rule) => {
              const pct = Math.min(100, Math.round(rule.ratio * 100));

              return (
                <div key={rule.name} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                    <span style={{ fontWeight: 500, color: "var(--text)" }}>{rule.name}</span>
                    <span className="mono" style={{ color: "var(--text-muted)" }}>
                      {rule.seen}
                    </span>
                  </div>
                  <div
                    style={{
                      height: "6px",
                      background: "var(--panel-raised)",
                      borderRadius: "3px",
                      overflow: "hidden",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        width: `${pct}%`,
                        height: "100%",
                        background: rule.fired ? "var(--red)" : pct > 0 ? "var(--amber)" : "var(--text-dim)",
                        borderRadius: "3px",
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "auto", lineHeight: "1.6" }}>
            Sophisticated adversaries purposely split actions into quiet fragments. By evaluating events in
            isolation, single-event alert rules remain blind to the complete attack kill-chain.
          </p>
        </div>
      </div>

      {/* Latest Raw Logs Preview */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="kicker">Raw lines, as they arrived</div>
            <h2 className="card-title">Latest logs</h2>
          </div>
          <Link href="/logs" className="btn btn-small">
            Open all {summary.events.toLocaleString()} events
          </Link>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: "90px" }}>ID</th>
                <th style={{ width: "100px" }}>Time (UTC)</th>
                <th style={{ width: "110px" }}>Source</th>
                <th>Raw Log Event</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((item) => (
                <tr key={item.id}>
                  <td style={{ color: "var(--lime)" }}>{item.id}</td>
                  <td>{item.time}</td>
                  <td>{item.source}</td>
                  <td className="primary-cell" style={{ wordBreak: "break-all" }}>
                    {item.raw}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
