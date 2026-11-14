"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../lib/state";
import { GraphNode } from "../lib/types";

export function AttackGraph() {
  const { caseData, selectedStep, setSelectedStep } = useApp();
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [visibleSteps, setVisibleSteps] = useState<number>(5);
  const [hasAutoReplayed, setHasAutoReplayed] = useState<boolean>(false);

  // Auto-replay on first load once graph data is ready
  useEffect(() => {
    if (caseData?.graph && !hasAutoReplayed) {
      setHasAutoReplayed(true);
      const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!prefersReduced) {
        setIsPlaying(true);
      }
    }
  }, [caseData, hasAutoReplayed]);

  // Replay Attack animation
  useEffect(() => {
    if (!isPlaying) return;

    let current = 1;
    setVisibleSteps(1);
    setSelectedStep(0);

    const interval = setInterval(() => {
      current++;
      if (current <= 5) {
        setVisibleSteps(current);
        setSelectedStep(current - 1);
      } else {
        setIsPlaying(false);
        clearInterval(interval);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [isPlaying, setSelectedStep]);

  const handleReplay = () => {
    if (isPlaying) return;
    setIsPlaying(true);
  };

  const handleStepSelect = (idx: number) => {
    if (isPlaying) {
      setIsPlaying(false);
      setVisibleSteps(5);
    }
    setSelectedStep(idx);
  };

  if (!caseData || !caseData.graph) {
    return <div className="card">No graph data.</div>;
  }

  const { graph, chain, volume } = caseData;
  const maxCount = Math.max(1, ...volume.map((pt) => pt.count));
  const nodes = graph.nodes;
  const nodeMap = new Map<string, GraphNode>(nodes.map((n) => [n.id, n]));

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Graph Toolbar */}
      <div
        className="card-header"
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
          background: "var(--panel)",
        }}
      >
        <div>
          <div className="kicker">Accounts, machines and outside addresses</div>
          <h2 className="card-title">Attack path</h2>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          {isPlaying && (
            <span className="mono" style={{ color: "var(--lime)", fontSize: "12px", fontWeight: 600 }}>
              Replaying: {chain[Math.min(visibleSteps - 1, 4)]?.time} UTC
            </span>
          )}
          <button
            className="btn btn-small btn-primary"
            onClick={handleReplay}
            disabled={isPlaying}
          >
            {isPlaying ? "Replaying..." : "Replay attack"}
          </button>
        </div>
      </div>

      {/* Main SVG Attack Canvas */}
      <div style={{ background: "var(--sidebar)", position: "relative" }}>
        <svg
          viewBox="0 0 860 500"
          className="svg-canvas"
          role="img"
          aria-label="Attack topology graph"
          style={{ width: "100%", height: "auto", display: "block" }}
        >
          <defs>
            <marker
              id="arrow-attack"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="var(--lime)" />
            </marker>
            <marker
              id="arrow-dashed"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="var(--amber)" />
            </marker>
            {/* Grid Pattern */}
            <pattern id="grid-dots" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="var(--border)" />
            </pattern>
          </defs>

          {/* Grid background */}
          <rect width="860" height="500" fill="url(#grid-dots)" />

          {/* Normal Background Edges */}
          {graph.edges.map((edge, i) => {
            const fromNode = nodeMap.get(edge.from);
            const toNode = nodeMap.get(edge.to);
            if (!fromNode || !toNode) return null;

            return (
              <line
                key={`normal-${i}`}
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke="var(--border-light)"
                strokeOpacity="0.55"
                strokeWidth="1"
              />
            );
          })}

          {/* Attack Path Edges */}
          {chain.map((st, idx) => {
            if (idx >= visibleSteps) return null;
            const fromNode = nodeMap.get(st.from);
            const toNode = nodeMap.get(st.to);
            if (!fromNode || !toNode) return null;

            const isSelected = selectedStep === idx;
            const isDashed = st.inferred;

            // Compute trimmed endpoints so arrows and packet pulses don't hide inside nodes
            const dx = toNode.x - fromNode.x;
            const dy = toNode.y - fromNode.y;
            const dist = Math.hypot(dx, dy) || 1;
            const pad = 22;
            const x1 = fromNode.x + (dx / dist) * pad;
            const y1 = fromNode.y + (dy / dist) * pad;
            const x2 = toNode.x - (dx / dist) * (pad + 4);
            const y2 = toNode.y - (dy / dist) * (pad + 4);

            // Compute midpoint for step number badge
            const midX = (fromNode.x + toNode.x) / 2;
            const midY = (fromNode.y + toNode.y) / 2;

            return (
              <g
                key={`chain-${st.step}`}
                onClick={() => handleStepSelect(idx)}
                style={{ cursor: "pointer" }}
              >
                {/* Hit area */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="transparent"
                  strokeWidth="24"
                />
                {/* Visual Line */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isDashed ? "var(--amber)" : "var(--lime)"}
                  strokeWidth={isSelected ? "4" : "2.2"}
                  strokeDasharray={isDashed ? "5 5" : undefined}
                  markerEnd={isDashed ? "url(#arrow-dashed)" : "url(#arrow-attack)"}
                />
                {/* Animated Packet Flow along Edge */}
                {!isDashed && (
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    className="e-p"
                  />
                )}
                {/* Step Badge */}
                <circle
                  cx={midX}
                  cy={midY}
                  r="10"
                  fill="var(--bg)"
                  stroke={isSelected ? "var(--text)" : "var(--lime)"}
                  strokeWidth={isSelected ? "2.5" : "1.5"}
                />
                <text
                  x={midX}
                  y={midY + 3.5}
                  textAnchor="middle"
                  fill={isSelected ? "var(--lime)" : "var(--text)"}
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                  fontWeight="700"
                >
                  {st.step}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((n) => {
            const isHit = n.state === "hit" && visibleSteps >= (n.step || 1);
            const isReachable = n.state === "reach" && visibleSteps >= 2;

            return (
              <g
                key={n.id}
                transform={`translate(${n.x}, ${n.y})`}
                style={{ cursor: "pointer" }}
              >
                {/* Node Outer Circle */}
                <circle
                  r={isHit ? "18" : isReachable ? "16" : "14"}
                  fill="var(--panel)"
                  stroke={
                    isHit ? "var(--lime)" : isReachable ? "var(--amber)" : "var(--border-light)"
                  }
                  strokeWidth={isHit || isReachable ? "2" : "1"}
                  strokeDasharray={isReachable ? "4 3" : undefined}
                />

                {/* Node Icon */}
                {n.type === "user" ? (
                  <path
                    d="M -4 4 A 4 4 0 0 1 4 4 M 0 -4 A 2.5 2.5 0 1 1 0 -9 A 2.5 2.5 0 1 1 0 -4"
                    fill="none"
                    stroke={isHit ? "var(--lime)" : "var(--text-muted)"}
                    strokeWidth="1.4"
                  />
                ) : n.type === "outside" ? (
                  <circle
                    r="5"
                    fill="none"
                    stroke={isHit ? "var(--red)" : "var(--text-dim)"}
                    strokeWidth="1.5"
                  />
                ) : (
                  <rect
                    x="-6"
                    y="-5"
                    width="12"
                    height="10"
                    rx="1.5"
                    fill="none"
                    stroke={isHit ? "var(--lime)" : isReachable ? "var(--amber)" : "var(--text-dim)"}
                    strokeWidth="1.4"
                  />
                )}

                {/* Node Label */}
                <text
                  y="26"
                  textAnchor="middle"
                  fill={isHit ? "var(--text)" : "var(--text-dim)"}
                  fontSize="11"
                  fontFamily="var(--font-mono)"
                  fontWeight={isHit ? "600" : "400"}
                >
                  {n.id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "18px",
          padding: "10px 20px",
          borderTop: "1px solid var(--border)",
          background: "var(--panel)",
          fontSize: "11px",
          color: "var(--text-muted)",
          flexWrap: "wrap",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--lime)" }} />
          Compromised
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              border: "1.5px dashed var(--amber)",
            }}
          />
          Reachable from a compromised account
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--border-light)" }} />
          Normal activity
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "14px", height: "2px", background: "var(--lime)" }} />
          Attack step
        </span>
      </div>

      {/* Bottom Timeline with Volume Bars */}
      <div
        style={{
          padding: "14px 20px",
          borderTop: "1px solid var(--border)",
          background: "var(--panel-raised)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
          <span className="kicker">Event volume, with the attack steps pinned</span>
          <span className="mono" style={{ fontSize: "11px", color: "var(--text-dim)" }}>
            03:00 to 04:30 UTC
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <svg viewBox="0 0 760 80" className="svg-canvas" style={{ minWidth: "540px" }}>
            {/* Background Bars */}
            {volume.map((pt, i) => {
              const x = 30 + i * (700 / volume.length);
              const h = (pt.count / maxCount) * 45;
              return (
                <rect
                  key={pt.start}
                  x={x}
                  y={60 - h}
                  width={700 / volume.length - 4}
                  height={h}
                  rx="1.5"
                  fill="var(--border)"
                />
              );
            })}

            {/* Time labels */}
            {[0, 15, 30, 45, 60, 75, 90].map((t) => {
              const x = 30 + (t / 90) * 700;
              const hr = 3 + Math.floor(t / 60);
              const mn = t % 60;
              const label = `0${hr}:${mn === 0 ? "00" : mn}`;
              return (
                <text
                  key={t}
                  x={x}
                  y="74"
                  fill="var(--text-dim)"
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                >
                  {label}
                </text>
              );
            })}

            {/* Plotted Attack Step Pins */}
            {chain.map((st, i) => {
              if (i >= visibleSteps) return null;
              const x = 30 + (st.minute / 90) * 700;
              const isSelected = selectedStep === i;

              return (
                <g
                  key={st.step}
                  onClick={() => handleStepSelect(i)}
                  style={{ cursor: "pointer" }}
                >
                  <line
                    x1={x}
                    y1="14"
                    x2={x}
                    y2="60"
                    stroke={isSelected ? "var(--lime)" : "var(--lime-border)"}
                    strokeWidth={isSelected ? "2" : "1"}
                  />
                  <circle
                    cx={x}
                    cy="14"
                    r="8"
                    fill={isSelected ? "var(--lime)" : "var(--bg)"}
                    stroke="var(--lime)"
                    strokeWidth="1.5"
                  />
                  <text
                    x={x}
                    y="17"
                    textAnchor="middle"
                    fill={isSelected ? "var(--bg)" : "var(--lime)"}
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    fontWeight="700"
                  >
                    {st.step}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}
