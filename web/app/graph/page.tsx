"use client";

import React from "react";
import { AttackGraph } from "../../components/AttackGraph";
import { EvidenceDrawer } from "../../components/EvidenceDrawer";

export default function GraphPage() {
  return (
    <div className="grid-wide">
      <AttackGraph />
      <EvidenceDrawer />
    </div>
  );
}
