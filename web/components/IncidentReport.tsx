"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../lib/state";

export function IncidentReport() {
  const router = useRouter();
  const { caseData, setSelectedStep, approvals } = useApp();
  const [copied, setCopied] = useState<boolean>(false);

  if (!caseData || !caseData.report) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No report generated. Run investigation first.</p>
      </div>
    );
  }

  const { verdict, report, chain, limits, actions } = caseData;

  const handleCitationClick = (stepNum: number) => {
    setSelectedStep(stepNum - 1);
    router.push("/graph");
  };

  const handleCopyText = async () => {
    const lines = [
      `CHIMERA INCIDENT INVESTIGATION REPORT`,
      `Case: 0114 · Acme Corp`,
      `Confidence: ${verdict.confidence}%`,
      `Status: ${verdict.label}`,
      `Date: 14 Nov 2026`,
      ``,
      `--- WHAT HAPPENED ---`,
      ...report.map((r) => `- ${r.text} [Cites: ${r.cites.join(", ")}]`),
      ``,
      `--- ATTACK SEQUENCE ---`,
      ...chain.map(
        (c) =>
          `[${c.time} UTC] Step ${c.step}: ${c.stage} (${c.technique}) - ${c.what} (${c.confidence}% sure)`
      ),
      ``,
      `--- WHAT THE LOGS CANNOT PROVE ---`,
      ...limits.map((l) => `- ${l}`),
      ``,
      `--- ACTIONS & APPROVALS ---`,
      ...actions.map((a) => `- [${approvals[a.id] ? "APPROVED" : "PENDING"}] ${a.kind}: ${a.text}`),
    ];

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div style={{ maxWidth: "860px", margin: "0 auto", width: "100%" }}>
      <div className="card" style={{ padding: "32px", gap: "24px", background: "var(--panel)" }}>
        {/* Report Header */}
        <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "20px" }}>
          <div className="kicker" style={{ color: "var(--lime)" }}>
            Formal Incident Summary · Case 0114
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: 700, margin: "6px 0 10px", color: "var(--text)" }}>
            Payroll Data Exfiltration at 04:07 UTC
          </h1>
          <div
            className="mono"
            style={{ display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-dim)", flexWrap: "wrap" }}
          >
            <span style={{ color: "var(--lime)" }}>{verdict.confidence}% Confidence</span>
            <span>Generated: 04:31 UTC · 14 Nov 2026</span>
            <span>Simulated Dataset (5,124 Events)</span>
          </div>
        </div>

        {/* What Happened Narrative */}
        <div>
          <h3 className="kicker" style={{ marginBottom: "10px" }}>
            01 / Narrative of Observed Facts
          </h3>
          <div style={{ fontSize: "14px", lineHeight: "1.7", color: "var(--text)" }}>
            {report.map((item, idx) => (
              <span key={idx} style={{ marginRight: "6px" }}>
                {item.text}
                <button
                  onClick={() => handleCitationClick(item.step)}
                  style={{
                    display: "inline-block",
                    padding: "1px 5px",
                    borderRadius: "3px",
                    background: "var(--lime-soft)",
                    border: "1px solid var(--lime-border)",
                    color: "var(--lime)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    marginLeft: "4px",
                    cursor: "pointer",
                  }}
                >
                  {item.cites.join(", ")} ↗
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Chronological Sequence Table */}
        <div>
          <h3 className="kicker" style={{ marginBottom: "10px" }}>
            02 / Reconstructed Chronology
          </h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "90px" }}>Time (UTC)</th>
                  <th>Observed Activity</th>
                  <th style={{ width: "150px" }}>MITRE Technique</th>
                  <th style={{ width: "80px" }}>Certainty</th>
                </tr>
              </thead>
              <tbody>
                {chain.map((c) => (
                  <tr key={c.step}>
                    <td>{c.time}</td>
                    <td className="primary-cell">{c.what}</td>
                    <td style={{ color: "var(--text-dim)", fontSize: "11px" }}>{c.technique}</td>
                    <td className="mono" style={{ color: c.confidence >= 80 ? "var(--lime)" : "var(--amber)" }}>
                      {c.confidence}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* What the Logs Cannot Prove */}
        <div>
          <h3 className="kicker" style={{ marginBottom: "10px", color: "var(--amber)" }}>
            03 / Forensic Blind Spots & Known Limitations
          </h3>
          <ul style={{ listStyle: "disc", paddingLeft: "20px", fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.7" }}>
            {limits.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>

        {/* Actions & Approvals */}
        <div>
          <h3 className="kicker" style={{ marginBottom: "10px" }}>
            04 / Incident Response Actions
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {actions.map((act) => {
              const approved = Boolean(approvals[act.id]);

              return (
                <div
                  key={act.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "var(--panel-raised)",
                    border: "1px solid var(--border)",
                    borderRadius: "4px",
                    fontSize: "12px",
                  }}
                >
                  <span>
                    <strong style={{ color: "var(--text-dim)", marginRight: "8px" }}>[{act.kind}]</strong>
                    {act.text}
                  </span>
                  <span
                    className={`pill ${approved ? "pill-lime" : ""}`}
                    style={{ fontSize: "10px" }}
                  >
                    {approved ? "Approved" : "Awaiting Authorization"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Copy Report Button */}
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: "18px" }}>
          <button className="btn btn-primary" onClick={handleCopyText}>
            {copied ? "✓ Copied to Clipboard!" : "Copy Report as Plain Text"}
          </button>
        </div>
      </div>
    </div>
  );
}
