"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useApp } from "../lib/state";

export function IncidentReport() {
  const router = useRouter();
  const { caseData, setSelectedStep, approvals } = useApp();
  const [copied, setCopied] = useState(false);

  if (!caseData || !caseData.report) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No report generated. Run investigation first.</p>
      </div>
    );
  }

  const { verdict, report, chain, limits, actions, summary, level, deleted } = caseData;

  function openCitation(step: number) {
    setSelectedStep(step - 1);
    router.push("/graph");
  }

  async function copyReport() {
    const lines = [
      "CHIMERA INCIDENT INVESTIGATION REPORT",
      `Confidence: ${verdict.confidence}%`,
      `Status: ${verdict.label}`,
      `Dataset: Simulated (${summary.events.toLocaleString()} events)`,
      `Stress level: ${level}% (${deleted.toLocaleString()} events deleted)`,
      "",
      "--- WHAT HAPPENED ---",
      ...report.map((item) => `- ${item.text} [Cites: ${item.cites.join(", ")}]`),
      "",
      "--- ATTACK SEQUENCE ---",
      ...chain.map(
        (step) =>
          `[${step.time} UTC] Step ${step.step}: ${step.stage} (${step.technique}) - ${step.what} (${step.confidence}% sure)`,
      ),
      "",
      "--- WHAT THE LOGS CANNOT PROVE ---",
      ...limits.map((limit) => `- ${limit}`),
      "",
      "--- ACTIONS & APPROVALS ---",
      ...actions.map((action) => {
        const approval = approvals[action.id];
        const state = approval
          ? `APPROVED by ${approval.approved_by} at ${new Date(approval.approved_at).toLocaleString()}`
          : "PENDING";
        return `- [${state}] ${action.kind}: ${action.text}`;
      }),
    ];

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div style={{ maxWidth: "860px", margin: "0 auto", width: "100%" }}>
      <div className="card" style={{ padding: "32px", gap: "24px", background: "var(--panel)" }}>
        <header style={{ borderBottom: "1px solid var(--border)", paddingBottom: "20px" }}>
          <div className="kicker" style={{ color: "var(--lime)" }}>Incident report</div>
          <h1 style={{ fontSize: "22px", fontWeight: 600, lineHeight: 1.35, margin: "6px 0 10px", color: "var(--text)" }}>
            {verdict.headline || verdict.label}
          </h1>
          <div
            className="mono"
            style={{ display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-dim)", flexWrap: "wrap" }}
          >
            <span style={{ color: "var(--lime)" }}>{verdict.confidence}% confidence</span>
            <span>{summary.events.toLocaleString()} simulated events</span>
            <span>
              Stress level {level}%, {deleted.toLocaleString()} events deleted
            </span>
          </div>
        </header>

        <section>
          <h2 className="report-h">What happened</h2>
          <div style={{ fontSize: "14px", lineHeight: 1.7, color: "var(--text)" }}>
            {report.map((item) => (
              <span key={`${item.step}-${item.cites.join("-")}`} style={{ marginRight: "6px" }}>
                {item.text}
                <button
                  type="button"
                  aria-label={`Open evidence for step ${item.step}: ${item.cites.join(", ")}`}
                  onClick={() => openCitation(item.step)}
                  style={{
                    display: "inline-block",
                    padding: "1px 5px",
                    background: "var(--lime-soft)",
                    border: "1px solid var(--lime-border)",
                    color: "var(--lime)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    marginLeft: "4px",
                  }}
                >
                  {item.cites.join(", ")}
                </button>
              </span>
            ))}
          </div>
        </section>

        <section>
          <h2 className="report-h">Timeline</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "90px" }}>Time (UTC)</th>
                  <th>Activity</th>
                  <th style={{ width: "150px" }}>ATT&amp;CK technique</th>
                  <th style={{ width: "80px" }}>Sure</th>
                </tr>
              </thead>
              <tbody>
                {chain.map((step) => (
                  <tr key={step.step}>
                    <td>{step.time}</td>
                    <td className="primary-cell">{step.what}</td>
                    <td style={{ color: "var(--text-dim)", fontSize: "11px" }}>{step.technique}</td>
                    <td className="mono" style={{ color: step.confidence >= 80 ? "var(--lime)" : "var(--amber)" }}>
                      {step.confidence}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="report-h">What this report cannot see</h2>
          <ul style={{ paddingLeft: "20px", fontSize: "13px", color: "var(--text-muted)", lineHeight: 1.7 }}>
            {limits.map((limit) => <li key={limit}>{limit}</li>)}
          </ul>
        </section>

        <section>
          <h2 className="report-h">Response actions</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {actions.map((action) => {
              const approval = approvals[action.id];
              return (
                <div
                  key={action.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "16px",
                    padding: "8px 12px",
                    background: "var(--panel-raised)",
                    border: "1px solid var(--border)",
                    fontSize: "12px",
                  }}
                >
                  <span>
                    <strong style={{ color: "var(--text-dim)", marginRight: "8px" }}>[{action.kind}]</strong>
                    {action.text}
                  </span>
                  <span style={{ display: "grid", justifyItems: "end", gap: "3px", flexShrink: 0 }}>
                    <span className={`pill ${approval ? "pill-lime" : ""}`} style={{ fontSize: "10px" }}>
                      {approval ? "Approved" : "Awaiting Authorization"}
                    </span>
                    {approval && (
                      <span style={{ color: "var(--text-dim)", fontSize: "10px" }}>
                        {approval.approved_by}, {new Date(approval.approved_at).toLocaleString()}
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        <footer
          style={{ borderTop: "1px solid var(--border)", paddingTop: "18px", display: "flex", gap: "10px", flexWrap: "wrap" }}
        >
          <a className="btn btn-primary" href={`/api/case/report.md?level=${level}`} download>
            Download as Markdown
          </a>
          <button className="btn" type="button" onClick={copyReport}>
            {copied ? "Copied to clipboard" : "Copy report as plain text"}
          </button>
        </footer>
      </div>
    </div>
  );
}
