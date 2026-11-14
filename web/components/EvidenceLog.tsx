"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "../lib/state";

type FilterType = "all" | "chain" | "weak" | "late";

export function EvidenceLog() {
  const router = useRouter();
  const { caseData, setSelectedStep } = useApp();
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  if (!caseData || !caseData.events) {
    return (
      <div className="card" style={{ padding: "40px", textAlign: "center" }}>
        <p className="kicker">No evidence log data available. Run investigation first.</p>
      </div>
    );
  }

  const events = caseData.events;

  const filteredEvents = events.filter((ev) => {
    // Filter by tab
    if (filter === "chain" && ev.step === null) return false;
    if (filter === "weak" && (ev.step !== null || ev.score < 0.3)) return false;
    if (filter === "late" && !ev.late) return false;

    // Filter by search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        ev.id.toLowerCase().includes(q) ||
        ev.source.toLowerCase().includes(q) ||
        ev.raw.toLowerCase().includes(q) ||
        ev.reasons.some((r) => r.toLowerCase().includes(q));
      if (!match) return false;
    }

    return true;
  });

  const handleStepClick = (stepNum: number) => {
    setSelectedStep(stepNum - 1);
    router.push("/graph");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Search and Filter Bar */}
      <div
        className="card"
        style={{
          padding: "14px 18px",
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
        }}
      >
        {/* Segmented Filter Buttons */}
        <div
          style={{
            display: "flex",
            gap: "4px",
            background: "var(--panel-raised)",
            padding: "3px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
          }}
        >
          {(
            [
              ["all", "All Events"],
              ["chain", "In Attack Chain"],
              ["weak", "Weak Signals"],
              ["late", "Arrived Late"],
            ] as [FilterType, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                padding: "6px 12px",
                borderRadius: "4px",
                fontSize: "12px",
                fontWeight: 500,
                color: filter === key ? "var(--text)" : "var(--text-muted)",
                background: filter === key ? "var(--panel)" : "transparent",
                border: filter === key ? "1px solid var(--border-light)" : "1px solid transparent",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div style={{ flex: "0 1 320px", width: "100%" }}>
          <input
            type="search"
            placeholder="Search by ID, machine, user or event..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "7px 12px",
              background: "var(--panel-raised)",
              border: "1px solid var(--border-light)",
              borderRadius: "6px",
              fontSize: "12px",
              color: "var(--text)",
              outline: "none",
            }}
          />
        </div>
      </div>

      {/* Forensic Log Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: "90px" }}>Event ID</th>
                <th style={{ width: "90px" }}>Time (UTC)</th>
                <th style={{ width: "110px" }}>Source</th>
                <th>Raw Event Line & Forensic Context</th>
                <th style={{ width: "140px" }}>Score & Reasons</th>
                <th style={{ width: "90px" }}>Chain Step</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "var(--text-dim)" }}>
                    No events matching filter criteria.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((ev) => {
                  const inChain = ev.step !== null;

                  return (
                    <tr
                      key={ev.id}
                      className={inChain ? "in-chain" : ""}
                      style={{
                        background: inChain ? "var(--accent-soft)" : undefined,
                      }}
                    >
                      <td style={{ color: inChain ? "var(--lime)" : "var(--text-muted)", fontWeight: 600 }}>
                        {ev.id}
                      </td>
                      <td>{ev.time}</td>
                      <td>{ev.source}</td>
                      <td className="primary-cell">
                        <div style={{ wordBreak: "break-all" }}>{ev.raw}</div>
                        <div style={{ display: "flex", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
                          {ev.late && (
                            <span className="pill pill-amber" style={{ fontSize: "9px", padding: "1px 5px" }}>
                              Late Arrival
                            </span>
                          )}
                          {ev.truth === "missed" && (
                            <span className="pill pill-red" style={{ fontSize: "9px", padding: "1px 5px" }}>
                              Planted, Missed
                            </span>
                          )}
                          {ev.truth === "false_link" && (
                            <span className="pill pill-amber" style={{ fontSize: "9px", padding: "1px 5px" }}>
                              Linked By Mistake
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            className="mono"
                            style={{
                              fontSize: "12px",
                              fontWeight: 600,
                              color: ev.score >= 0.6 ? "var(--lime)" : ev.score >= 0.3 ? "var(--amber)" : "var(--text-dim)",
                            }}
                          >
                            {ev.score.toFixed(2)}
                          </span>
                          <div
                            style={{
                              width: "50px",
                              height: "4px",
                              background: "var(--panel-raised)",
                              borderRadius: "2px",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${Math.round(ev.score * 100)}%`,
                                height: "100%",
                                background:
                                  ev.score >= 0.6 ? "var(--lime)" : ev.score >= 0.3 ? "var(--amber)" : "var(--text-dim)",
                              }}
                            />
                          </div>
                        </div>
                        {ev.reasons.length > 0 && (
                          <div style={{ fontSize: "10px", color: "var(--text-dim)", marginTop: "2px" }}>
                            {ev.reasons.join(", ")}
                          </div>
                        )}
                      </td>
                      <td>
                        {inChain ? (
                          <button
                            onClick={() => handleStepClick(ev.step as number)}
                            className="pill pill-lime"
                            style={{ cursor: "pointer", fontSize: "10px", fontWeight: 700 }}
                          >
                            Step {ev.step} ↗
                          </button>
                        ) : (
                          <span style={{ color: "var(--text-dim)", fontSize: "11px" }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div
          style={{
            padding: "10px 18px",
            borderTop: "1px solid var(--border)",
            background: "var(--panel-raised)",
            fontSize: "11px",
            color: "var(--text-dim)",
          }}
        >
          Showing {filteredEvents.length} events (of {caseData.summary.events.toLocaleString()} total in
          dataset). Green-tinted rows represent confirmed links inside the reconstructed attack chain.
        </div>
      </div>
    </div>
  );
}
