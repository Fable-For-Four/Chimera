"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../lib/state";
import { ChainStep, GraphNode } from "../lib/types";
import { timeWindow } from "../lib/time";

const STEP_MS = 1300;
const RADIUS = { hit: 20, reach: 17, normal: 15 };
const ARROW = 9;
const BUCKET_MINUTES = 5;
const TIMELINE_X = 30;
const TIMELINE_WIDTH = 700;
const PIN_GAP = 18;

function NodeIcon({ type }: { type: GraphNode["type"] }) {
  if (type === "user") {
    return (
      <g className="g-icon">
        <circle cx="0" cy="-3.5" r="3.2" />
        <path d="M -6.5 7 C -6.5 2 6.5 2 6.5 7" />
      </g>
    );
  }
  if (type === "outside") {
    return (
      <g className="g-icon">
        <circle r="6.5" />
        <ellipse rx="2.8" ry="6.5" />
        <line x1="-6.5" y1="0" x2="6.5" y2="0" />
      </g>
    );
  }
  return (
    <g className="g-icon">
      <rect x="-6.5" y="-7" width="13" height="5.5" />
      <rect x="-6.5" y="1.5" width="13" height="5.5" />
      <line x1="-4" y1="-4.25" x2="-2" y2="-4.25" />
      <line x1="-4" y1="4.25" x2="-2" y2="4.25" />
    </g>
  );
}

const BADGE_SPOTS = [0.5, 0.42, 0.58, 0.35, 0.65, 0.28, 0.72];

function badgeSpot(from: GraphNode, to: GraphNode, nodes: GraphNode[]) {
  const clearance = (x: number, y: number) =>
    Math.min(
      ...nodes.map((n) => {
        const r = RADIUS[n.state];
        const toNode = Math.hypot(x - n.x, y - n.y) - r;
        const toLabel = Math.hypot((x - n.x) / 2.2, y - (n.y + r + 11)) - 6;
        return Math.min(toNode, toLabel);
      }),
    );
  let best = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2, room: -Infinity };
  for (const t of BADGE_SPOTS) {
    const x = from.x + (to.x - from.x) * t;
    const y = from.y + (to.y - from.y) * t;
    const room = clearance(x, y);
    if (room > best.room + 4) best = { x, y, room };
  }
  return best;
}

const LOOP_DIRECTIONS = [-45, -135, 45, 135, -90, 0, 180];
const LOOP_REACH = 44;

function loopGeometry(node: GraphNode, nodes: GraphNode[]) {
  const r = RADIUS[node.state];
  const point = (deg: number, dist: number) => {
    const rad = (deg * Math.PI) / 180;
    return { x: node.x + Math.cos(rad) * dist, y: node.y + Math.sin(rad) * dist };
  };
  const room = (deg: number) => {
    const tip = point(deg, r + LOOP_REACH);
    return Math.min(
      ...nodes.filter((n) => n.id !== node.id).map((n) => Math.hypot(tip.x - n.x, tip.y - n.y)),
    );
  };
  const dir = LOOP_DIRECTIONS.reduce((best, deg) => (room(deg) > room(best) + 4 ? deg : best));
  const p1 = point(dir - 28, r + 3);
  const c1 = point(dir - 34, r + LOOP_REACH);
  const c2 = point(dir + 34, r + LOOP_REACH);
  const p2 = point(dir + 28, r + 3);
  const angle = (Math.atan2(p2.y - c2.y, p2.x - c2.x) * 180) / Math.PI;
  const badge = point(dir, r + LOOP_REACH * 0.78);
  return {
    d: `M ${p1.x} ${p1.y} C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${p2.x} ${p2.y}`,
    x2: p2.x,
    y2: p2.y,
    angle,
    badge,
  };
}

function edgeGeometry(from: GraphNode, to: GraphNode) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  const start = RADIUS[from.state] + 4;
  const end = RADIUS[to.state] + 4;
  return {
    x1: from.x + ux * start,
    y1: from.y + uy * start,
    x2: to.x - ux * end,
    y2: to.y - uy * end,
    lineEndX: to.x - ux * (end + ARROW - 1),
    lineEndY: to.y - uy * (end + ARROW - 1),
    angle: (Math.atan2(dy, dx) * 180) / Math.PI,
  };
}

function nodeTitle(n: GraphNode, chain: ChainStep[]) {
  const kind = n.type === "outside" ? "outside address" : n.type;
  if (n.state === "hit") return `${n.id}, ${kind}, used in step ${n.step ?? chain[0]?.step}`;
  if (n.state === "reach") return `${n.id}, ${kind}, reachable from a compromised account`;
  return `${n.id}, ${kind}, normal activity`;
}

export function AttackGraph() {
  const { caseData, selectedStep, setSelectedStep } = useApp();
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [shownSteps, setShownSteps] = useState<number | null>(null);
  const [replayId, setReplayId] = useState<number>(0);
  const [hasAutoReplayed, setHasAutoReplayed] = useState<boolean>(false);
  const totalSteps = caseData?.chain.length ?? 0;

  useEffect(() => {
    if (caseData?.graph && !hasAutoReplayed) {
      setHasAutoReplayed(true);
      const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!prefersReduced && totalSteps > 0) {
        setIsPlaying(true);
      }
    }
  }, [caseData, hasAutoReplayed, totalSteps]);

  useEffect(() => {
    if (!isPlaying) return;

    let current = 1;
    setReplayId((id) => id + 1);
    setShownSteps(1);
    setSelectedStep(0);

    const interval = setInterval(() => {
      current++;
      if (current <= totalSteps) {
        setShownSteps(current);
        setSelectedStep(current - 1);
      } else {
        setIsPlaying(false);
        setShownSteps(null);
        clearInterval(interval);
      }
    }, STEP_MS);

    return () => clearInterval(interval);
  }, [isPlaying, setSelectedStep, totalSteps]);

  const handleReplay = () => {
    if (isPlaying) return;
    setIsPlaying(true);
  };

  const handleStepSelect = (idx: number) => {
    if (isPlaying) {
      setIsPlaying(false);
      setShownSteps(null);
    }
    setSelectedStep(idx);
  };

  if (!caseData || !caseData.graph) {
    return <div className="card">No graph data.</div>;
  }

  const { graph, chain, volume } = caseData;
  const visible = shownSteps ?? chain.length;
  const maxCount = Math.max(1, ...volume.map((pt) => pt.count));
  const axisMinutes = Math.max(1, volume.length * BUCKET_MINUTES);
  const barStep = TIMELINE_WIDTH / Math.max(1, volume.length);
  const nodes = graph.nodes;
  const nodeMap = new Map<string, GraphNode>(nodes.map((n) => [n.id, n]));
  const active = chain[selectedStep];
  const activeIds = new Set(active ? [active.from, active.to] : []);
  const chainKeys = new Set(chain.slice(0, visible).flatMap((s) => [`${s.from}>${s.to}`, `${s.to}>${s.from}`]));

  const selectNode = (id: string) => {
    const idx = chain.findIndex((s) => s.to === id);
    const fallback = chain.findIndex((s) => s.from === id);
    if (idx >= 0) handleStepSelect(idx);
    else if (fallback >= 0) handleStepSelect(fallback);
  };

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
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
            <span className="mono" style={{ color: "var(--accent)", fontSize: "12px", fontWeight: 600 }}>
              Step {Math.min(visible, chain.length)} of {chain.length}, {chain[Math.min(visible, chain.length) - 1]?.time} UTC
            </span>
          )}
          <button className="btn btn-small btn-primary" onClick={handleReplay} disabled={isPlaying || chain.length === 0}>
            {isPlaying ? "Replaying..." : "Replay attack"}
          </button>
        </div>
      </div>

      <div style={{ background: "var(--sidebar)", position: "relative" }}>
        <svg
          viewBox="0 0 860 500"
          className="svg-canvas attack-graph"
          role="img"
          aria-label="Attack graph: accounts, machines and outside addresses, with the attack steps drawn in order"
        >
          <defs>
            <pattern id="grid-dots" width="24" height="24" patternUnits="userSpaceOnUse">
              <rect x="1.5" y="1.5" width="1" height="1" fill="var(--border-light)" />
            </pattern>
          </defs>

          <rect width="860" height="500" fill="url(#grid-dots)" />

          <g className="g-background">
            {graph.edges.map((edge, i) => {
              const fromNode = nodeMap.get(edge.from);
              const toNode = nodeMap.get(edge.to);
              if (!fromNode || !toNode || chainKeys.has(`${edge.from}>${edge.to}`)) return null;
              return (
                <line key={`bg-${i}`} x1={fromNode.x} y1={fromNode.y} x2={toNode.x} y2={toNode.y} />
              );
            })}
          </g>

          {chain.map((st, idx) => {
            if (idx >= visible) return null;
            const fromNode = nodeMap.get(st.from);
            const toNode = nodeMap.get(st.to);
            if (!fromNode || !toNode) return null;

            const isLoop = fromNode.id === toNode.id;
            const g = edgeGeometry(fromNode, toNode);
            const loop = isLoop ? loopGeometry(fromNode, nodes) : null;
            const badge = loop ? loop.badge : badgeSpot(fromNode, toNode, nodes);
            const tip = loop ?? g;
            const edgePath = loop ? loop.d : `M ${g.x1} ${g.y1} L ${g.lineEndX} ${g.lineEndY}`;
            const isSelected = selectedStep === idx;
            const kind = st.inferred ? "inferred" : "seen";

            return (
              <g
                key={`chain-${replayId}-${st.step}`}
                className={`g-step ${kind}${isSelected ? " sel" : ""}`}
                onClick={() => handleStepSelect(idx)}
              >
                <title>{`Step ${st.step}: ${st.what}`}</title>
                <path d={edgePath} className="g-hit" />
                <path d={edgePath} pathLength={1} className="g-edge" />
                <path
                  d={`M 0 0 L ${-ARROW} ${-ARROW / 2} L ${-ARROW} ${ARROW / 2} Z`}
                  transform={`translate(${tip.x2} ${tip.y2}) rotate(${tip.angle})`}
                  className="g-arrow"
                />
                {isSelected && !st.inferred && (
                  <circle r="3" className="g-dot">
                    <animateMotion dur="1.4s" repeatCount="indefinite" path={edgePath} />
                  </circle>
                )}
                <g transform={`translate(${badge.x} ${badge.y})`} className="g-badge">
                  <rect x="-10" y="-10" width="20" height="20" />
                  <text y="3.5" textAnchor="middle">
                    {st.step}
                  </text>
                </g>
              </g>
            );
          })}

          {nodes.map((n) => {
            const isHit = n.state === "hit" && visible >= (n.step ?? 1);
            const isReach = n.state === "reach" && visible >= Math.min(2, chain.length);
            const state = isHit ? "hit" : isReach ? "reach" : "normal";
            const r = RADIUS[n.state];
            const inChain = chain.some((s) => s.from === n.id || s.to === n.id);
            const isActive = activeIds.has(n.id) && (isHit || isReach);

            return (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                className={`g-node ${state} ${n.type}${isActive ? " active" : ""}${inChain ? " clickable" : ""}`}
                onClick={inChain ? () => selectNode(n.id) : undefined}
              >
                <title>{nodeTitle(n, chain)}</title>
                {isActive && <circle r={r} className="g-halo" />}
                {isHit && <circle key={`burst-${replayId}`} r={r} className="g-burst" />}
                <circle r={r} className="g-ring" />
                <NodeIcon type={n.type} />
                <text y={r + 15} textAnchor="middle" className="g-label">
                  {n.id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="graph-legend">
        <span>
          <span className="legend-ring hit" />
          Compromised
        </span>
        <span>
          <span className="legend-ring outside" />
          Outside address the attacker used
        </span>
        <span>
          <span className="legend-ring reach" />
          Reachable from a compromised account
        </span>
        <span>
          <span className="legend-ring" />
          Normal activity
        </span>
        <span>
          <span className="legend-line" />
          Attack step
        </span>
      </div>

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
            {timeWindow(volume)}
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <svg viewBox="0 0 760 80" className="svg-canvas" style={{ minWidth: "540px" }}>
            {volume.map((pt, i) => {
              const h = (pt.count / maxCount) * 45;
              return (
                <rect
                  key={pt.start}
                  x={TIMELINE_X + i * barStep}
                  y={60 - h}
                  width={Math.max(1, barStep - 4)}
                  height={h}
                  fill="var(--border)"
                />
              );
            })}

            {volume.map((pt, i) =>
              i % 3 === 0 ? (
                <text
                  key={`t-${pt.start}`}
                  x={TIMELINE_X + i * barStep}
                  y="74"
                  fill="var(--text-dim)"
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                >
                  {pt.start}
                </text>
              ) : null,
            )}

            {chain.map((st, i) => {
              if (i >= visible) return null;
              const pinX = (s: ChainStep) => TIMELINE_X + (s.minute / axisMinutes) * TIMELINE_WIDTH;
              const x = pinX(st);
              const crowd = chain.slice(0, i).filter((s) => Math.abs(pinX(s) - x) < PIN_GAP).length;
              const bx = x + crowd * PIN_GAP;
              const isSelected = selectedStep === i;

              return (
                <g
                  key={`pin-${replayId}-${st.step}`}
                  className={`t-pin${isSelected ? " sel" : ""}`}
                  onClick={() => handleStepSelect(i)}
                >
                  <title>{`Step ${st.step} at ${st.time} UTC`}</title>
                  <path d={`M ${x} 60 L ${x} 26 L ${bx} 22`} />
                  <rect x={bx - 8} y="6" width="16" height="16" />
                  <text x={bx} y="17.5" textAnchor="middle">
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
