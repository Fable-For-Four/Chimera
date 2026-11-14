"use client";

import React from "react";
import { StressLab } from "../../components/StressLab";

export default function StressPage() {
  return (
    <div>
      <header className="page-head">
        <h1>Stress test</h1>
        <p>Delete a share of the logs at random, delay the rest, and see whether the engine still finds the same chain.</p>
      </header>

      <StressLab />
    </div>
  );
}
