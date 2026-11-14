"use client";

import React from "react";
import Link from "next/link";
import { useApp } from "../lib/state";
import type { Night } from "../lib/types";

const CASES: [Night, string, string][] = [
  ["attack", "Payroll data theft", "Stolen VPN password, admin rights, payroll files read and sent out."],
  ["stopped", "Break-in stopped early", "Stolen password and admin rights, but cut off before any data left."],
  ["gap", "Theft with a missing log", "The same theft, but the domain controller log went silent mid-attack."],
  ["quiet", "Mail server flood", "A flood of connections from one address. Noisy, but no break-in."],
  ["spray", "Failed password spray", "One address tries a password on many accounts. Nobody gets in."],
  ["late_work", "Employee working late", "A real employee signs in from home at 3 a.m. and opens her own files."],
  ["random", "Payroll theft, fresh background", "The theft again, inside a new random night of normal activity."],
];

export function Start() {
  const { intake, user, isRunning, runInvestigation, night, setNight } = useApp();

  if (!intake) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">Loading the logs…</p>
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
          <div className="metric-val">{summary.late}</div>
          <div className="metric-label">Arrived late, out of order</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{summary.alerts_fired}</div>
          <div className="metric-label">Alerts fired</div>
        </div>
      </div>

      {/* Main Grid: Volume & Alerts */}
      <div className="grid-2">
        {/* Left: Volume & CTA */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Events per 5 minutes, 03:00 to 04:30 UTC</h2>
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
                {summary.alerts_fired === 0
                  ? "No alert fired across the whole night."
                  : `${summary.alerts_fired} of ${alert_rules.length} alerts fired.`}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Alert rules read one line at a time. The investigation connects them.
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", flexWrap: "wrap" }}>
              <label className="case-picker">
                <span>Test case</span>
                <select
                  value={night}
                  onChange={(e) => setNight(e.target.value as Night)}
                  disabled={isRunning}
                >
                  {CASES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <small>{CASES.find(([value]) => value === night)?.[2]}</small>
              </label>
              <button
                className="btn btn-primary"
                style={{ marginTop: "21px" }}
                onClick={runInvestigation}
                disabled={isRunning || user?.role === "viewer"}
              >
                {isRunning ? "Running..." : "Run investigation"}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Alert Rules */}
        <div className="card">
          <div className="card-header">
            <div>
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
            Each rule checks one line against a limit. An attack split into small steps stays under every
            limit.
          </p>
        </div>
      </div>

      {/* Latest Raw Logs Preview */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Latest logs, in the order they arrived</h2>
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
                <th>Log line</th>
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
