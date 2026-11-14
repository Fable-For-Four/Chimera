"use client";

import React from "react";
import Link from "next/link";
import { useApp } from "../lib/state";

const WEAK_SIGNAL_SCORE = 0.3;

export function NoChain() {
  const { caseData } = useApp();

  if (!caseData) return null;

  const { verdict, summary, stages, events, truth_score } = caseData;
  const weakSignals = events.filter((e) => e.score >= WEAK_SIGNAL_SCORE).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="kicker">Verdict</div>
            <h2 className="card-title">{verdict.label}</h2>
          </div>
          <span className="pill pill-lime">No attack chain</span>
        </div>
        <p style={{ fontSize: "15px", color: "var(--text)", lineHeight: "1.6" }}>{verdict.headline}</p>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.6", marginTop: "8px" }}>
          {weakSignals > 0
            ? `${weakSignals.toLocaleString()} events looked unusual on their own, but none of them shared an account, machine or address closely enough in time to form an attack story.`
            : "No event stood out from its baseline."}
        </p>
      </div>

      <div className="grid-2" style={{ gap: "12px" }}>
        <div className="metric-box">
          <div className="metric-val">{summary.events.toLocaleString()}</div>
          <div className="metric-label">Events investigated from {summary.sources} log sources</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{weakSignals.toLocaleString()}</div>
          <div className="metric-label">Weak signals scored but not linked</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{summary.late.toLocaleString()}</div>
          <div className="metric-label">Late logs put back in order</div>
        </div>
        <div className="metric-box">
          <div className="metric-val">{summary.alerts_fired}</div>
          <div className="metric-label">Old alert rules fired</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="kicker">How the case was worked</div>
            <h3 className="card-title">Every stage ran</h3>
          </div>
          <Link href="/logs" className="btn btn-small">
            See the scored events →
          </Link>
        </div>
        <ul className="stages">
          {stages.map((stage) => (
            <li key={stage.name} className="ok">
              <span className="dot">✓</span>
              <b>{stage.name}</b>
              <span className="res">
                <strong>{stage.result}</strong>
                <span>{stage.does}</span>
              </span>
              <span className="ms">{stage.seconds}s</span>
            </li>
          ))}
        </ul>
      </div>

      {truth_score.planted > 0 && (
        <div className="card">
          <div className="kicker">Score against the truth</div>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.6", marginTop: "6px" }}>
            This dataset has {truth_score.planted.toLocaleString()} planted events and {truth_score.found} of them
            were linked. Chimera looks for a multi-step intrusion across systems, so activity that does not form one
            is reported as no chain rather than guessed at.
          </p>
        </div>
      )}
    </div>
  );
}
