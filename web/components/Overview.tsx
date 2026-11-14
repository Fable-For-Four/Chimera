"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../lib/state";
import type { ChainStep } from "../lib/types";

export function Overview() {
  const router = useRouter();
  const { caseData, setSelectedStep, approvals, approveAction, user } = useApp();
  const [selectedQuestion, setSelectedQuestion] = useState<number>(-1);

  if (!caseData || !caseData.verdict) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No case data loaded.</p>
      </div>
    );
  }

  const { verdict, chain, hypotheses, stages, actions, questions } = caseData;
  const isFound = verdict.found;
  const confidence = verdict.confidence;

  const handleStepClick = (stepIdx: number) => {
    setSelectedStep(stepIdx);
    router.push("/graph");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Verdict Hero Card */}
      <div
        className="card"
        style={{
          borderLeft: `4px solid ${confidence >= 70 ? "var(--lime)" : "var(--amber)"}`,
          background: "var(--panel)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", gap: "28px", alignItems: "center", flexWrap: "wrap" }}>
          {/* Radial Confidence Gauge */}
          <div style={{ position: "relative", width: "110px", height: "110px", flexShrink: 0 }}>
            <svg viewBox="0 0 110 110" style={{ transform: "rotate(-90deg)", width: "100%", height: "100%" }}>
              <circle
                cx="55"
                cy="55"
                r="46"
                fill="none"
                stroke="var(--panel-raised)"
                strokeWidth="8"
              />
              <circle
                cx="55"
                cy="55"
                r="46"
                fill="none"
                stroke={confidence >= 70 ? "var(--lime)" : "var(--amber)"}
                strokeWidth="8"
                strokeDasharray="289"
                strokeDashoffset={289 * (1 - confidence / 100)}
                strokeLinecap="round"
                style={{ transition: "stroke-dashoffset 0.5s ease" }}
              />
            </svg>
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
              }}
            >
              <span className="mono" style={{ fontSize: "24px", fontWeight: 700, color: "var(--text)" }}>
                {confidence}%
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                confidence
              </span>
            </div>
          </div>

          {/* Verdict Text & Facts */}
          <div style={{ flex: 1, minWidth: "280px" }}>
            <div className="kicker" style={{ color: confidence >= 70 ? "var(--lime)" : "var(--amber)" }}>
              Verdict
            </div>
            <h1 style={{ fontSize: "26px", fontWeight: 700, margin: "2px 0 6px", color: "var(--text)" }}>
              {verdict.label}
            </h1>
            <p style={{ fontSize: "14px", color: "var(--text-muted)", maxWidth: "800px", lineHeight: "1.6" }}>
              {verdict.headline}
            </p>

            {/* Key Facts Row */}
            {isFound && verdict.entry_point && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "14px",
                  marginTop: "16px",
                  paddingTop: "16px",
                  borderTop: "1px solid var(--border)",
                }}
              >
                <div>
                  <div className="kicker">Entry point</div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                    {verdict.entry_point.account}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{verdict.entry_point.text}</div>
                </div>

                <div>
                  <div className="kicker">Blast radius</div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                    {verdict.blast_radius?.accounts.length} accounts, {verdict.blast_radius?.touched.length} machines
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {verdict.blast_radius?.reachable.join(", ")} reachable
                  </div>
                </div>

                <div>
                  <div className="kicker">Data taken</div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                    {verdict.data_at_risk?.files.toLocaleString()} payroll files
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {(Number(verdict.data_at_risk?.bytes_out || 0) / (1024 * 1024 * 1024)).toFixed(1)} GB outbound
                  </div>
                </div>

                <div>
                  <div className="kicker">Weakest link</div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--amber)" }}>
                    {verdict.weakest_step ? `Step ${verdict.weakest_step}` : "None"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {chain.find((s) => s.step === verdict.weakest_step)?.what}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {isFound && chain.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">How the attack unfolded ({chain.length} connected steps)</h2>
            <span className="kicker">Select a step to open its evidence</span>
          </div>
          <Waterfall chain={chain} onSelect={handleStepClick} />
        </div>
      )}

      {/* 3-Column Context Grid */}
      <div className="grid-3">
        {/* Hypotheses Tested */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">Tested against the chain</div>
              <h3 className="card-title">Other explanations</h3>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {hypotheses.map((hyp, i) => (
              <div key={hyp.name} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                  <span style={{ fontWeight: 600, color: "var(--text)" }}>{hyp.name}</span>
                  <span className="mono" style={{ color: i === 0 ? "var(--lime)" : "var(--text-muted)" }}>
                    {hyp.share}%
                  </span>
                </div>
                <div
                  style={{
                    height: "4px",
                    background: "var(--panel-raised)",
                    borderRadius: "2px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${hyp.share}%`,
                      height: "100%",
                      background: i === 0 ? "var(--lime)" : "var(--border-focus)",
                    }}
                  />
                </div>
                <ul style={{ listStyle: "none", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  {hyp.fits.map((f) => (
                    <li key={f} style={{ display: "flex", gap: "6px" }}>
                      <span style={{ color: "var(--lime)" }}>fits</span> {f}
                    </li>
                  ))}
                  {hyp.breaks.map((b) => (
                    <li key={b} style={{ display: "flex", gap: "6px" }}>
                      <span style={{ color: "var(--red)" }}>breaks</span> {b}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Execution Audit */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">How the case was worked</div>
              <h3 className="card-title">
                Stage durations ({stages.reduce((total, s) => total + s.seconds, 0).toFixed(2)}s)
              </h3>
            </div>
          </div>

          <ul className="stages compact">
            {stages.map((st) => (
              <li key={st.name} className="ok">
                <span className="dot">✓</span>
                <b>{st.name}</b>
                <span className="res">{st.result}</span>
                <span className="ms">{st.seconds}s</span>
              </li>
            ))}
          </ul>
          <div style={{ marginTop: "14px", fontSize: "11px", color: "var(--text-dim)" }}>
            Every stage runs locally with fixed rules. The same logs give the same answer.
          </div>
        </div>

        {/* Action Approvals */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="kicker">Nothing runs until an analyst approves</div>
              <h3 className="card-title">Recommended actions</h3>
            </div>
            <span className="mono" style={{ fontSize: "11px", color: "var(--text-dim)" }}>
              {Object.keys(approvals).length} of {actions.length} approved
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {actions.map((act) => {
              const approved = Boolean(approvals[act.id]);

              return (
                <div
                  key={act.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "10px",
                    padding: "8px 0",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <div>
                    <span className="kicker" style={{ color: "var(--text-dim)" }}>
                      {act.kind}
                    </span>
                    <div style={{ fontSize: "12px", color: "var(--text)" }}>{act.text}</div>
                  </div>

                  {approved ? (
                    <span className="btn btn-small btn-done">Approved</span>
                  ) : (
                    <button
                      className="btn btn-small"
                      onClick={() => approveAction(act.id)}
                      disabled={user?.role === "viewer"}
                      title={user?.role === "viewer" ? "Viewers cannot approve actions" : "Approve action"}
                    >
                      Approve
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <p style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "auto" }}>
            Chimera recommends containment protocols, but no network changes take place until an analyst approves.
          </p>
        </div>
      </div>

      {/* Ask The Case Q&A */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="kicker">Every answer cites log lines</div>
            <h3 className="card-title">Ask the case</h3>
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {questions.map((q, idx) => (
            <button
              key={q.q}
              className={`btn ${selectedQuestion === idx ? "btn-primary" : ""}`}
              onClick={() => setSelectedQuestion(selectedQuestion === idx ? -1 : idx)}
            >
              {q.q}
            </button>
          ))}
        </div>

        {selectedQuestion >= 0 && (
          <div
            style={{
              background: "var(--panel-raised)",
              borderRadius: "6px",
              padding: "16px 20px",
              border: "1px solid var(--border-light)",
              marginTop: "8px",
            }}
          >
            <div style={{ fontSize: "13px", color: "var(--text)", lineHeight: "1.6" }}>
              {questions[selectedQuestion].a}
            </div>
            <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
              <span className="kicker" style={{ alignSelf: "center" }}>
                Cited Exhibits:
              </span>
              {questions[selectedQuestion].cites.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleStepClick(c.step - 1)}
                  style={{
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "var(--lime-soft)",
                    border: "1px solid var(--lime-border)",
                    color: "var(--lime)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                  }}
                >
                  {c.id} (Step {c.step}) ↗
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const TICK_MINUTES = 15;

function Waterfall({ chain, onSelect }: { chain: ChainStep[]; onSelect: (idx: number) => void }) {
  const lastMinute = Math.max(...chain.map((s) => s.minute));
  const axisEnd = Math.max(TICK_MINUTES, Math.ceil((lastMinute + 1) / TICK_MINUTES) * TICK_MINUTES);
  const ticks = Array.from({ length: axisEnd / TICK_MINUTES + 1 }, (_, i) => i * TICK_MINUTES);
  const pct = (minute: number) => `${(minute / axisEnd) * 100}%`;

  return (
    <div className="wf">
      <div className="wf-row wf-head" aria-hidden="true">
        <span />
        <span>Step</span>
        <span className="wf-axis">
          {ticks.map((t) => (
            <span key={t} className="wf-tick" style={{ left: pct(t) }}>
              +{t}m
            </span>
          ))}
        </span>
        <span className="wf-num">Time</span>
        <span className="wf-num">Sure</span>
      </div>

      {chain.map((st, idx) => {
        const next = chain[idx + 1];
        const gap = next ? next.minute - st.minute : 0;
        const strong = st.confidence >= 80;

        return (
          <button key={st.step} className="wf-row wf-step" onClick={() => onSelect(idx)}>
            <span className="wf-index">{st.step}</span>
            <span className="wf-label">
              <span className="wf-stage">
                {st.stage}
                <span className="wf-technique">{st.technique.split(" ")[0]}</span>
              </span>
              <span className="wf-what">{st.what}</span>
            </span>
            <span className="wf-track">
              {ticks.map((t) => (
                <span key={t} className="wf-grid" style={{ left: pct(t) }} />
              ))}
              <span
                className={`wf-bar${strong ? "" : " wf-bar-weak"}${st.inferred ? " wf-bar-inferred" : ""}`}
                style={{ left: pct(st.minute), width: gap > 0 ? pct(gap) : undefined }}
              />
              {gap > 0 && (
                <span className="wf-gap" style={{ left: `calc(${pct(st.minute + gap)} + 6px)` }}>
                  {gap}m
                </span>
              )}
            </span>
            <span className="wf-num">{st.time}</span>
            <span className={`wf-num ${strong ? "wf-sure" : "wf-unsure"}`}>{st.confidence}%</span>
          </button>
        );
      })}
    </div>
  );
}
