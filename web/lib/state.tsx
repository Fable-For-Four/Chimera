"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { CaseData, IntakeData, User, Approval } from "./types";
import {
  getMe,
  getIntake,
  getCase,
  getStressCase,
  postRunInvestigation,
  postApproveAction,
  getApprovals,
} from "./api";

interface AppContextType {
  user: User | null;
  intake: IntakeData | null;
  caseData: CaseData | null;
  selectedStep: number;
  stressLevel: number;
  isRunning: boolean;
  approvals: Record<string, Approval>;
  error: string | null;
  setSelectedStep: (step: number) => void;
  setStressLevel: (level: number) => Promise<void>;
  runInvestigation: () => Promise<void>;
  finishInvestigation: () => void;
  approveAction: (actionId: string) => Promise<void>;
  refreshCase: () => Promise<void>;
  resetCase: () => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [intake, setIntake] = useState<IntakeData | null>(null);
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [selectedStep, setSelectedStep] = useState<number>(0);
  const [stressLevel, setStressLevelState] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [approvals, setApprovals] = useState<Record<string, Approval>>({});
  const [error, setError] = useState<string | null>(null);

  // Initial data bootstrap
  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const [me, intakeData, approvalsList] = await Promise.all([
          getMe(),
          getIntake(),
          getApprovals(),
        ]);

        if (!mounted) return;
        setUser(me);
        setIntake(intakeData);

        const approvalMap: Record<string, Approval> = {};
        for (const app of approvalsList) {
          approvalMap[app.action_id] = app;
        }
        setApprovals(approvalMap);

        // Try loading existing case if already run
        try {
          const currentCase = await getCase();
          if (mounted && currentCase) setCaseData(currentCase);
        } catch {
          // No case yet; remains on Start intake
        }
      } catch (err: unknown) {
        if (mounted) setError(err instanceof Error ? err.message : "Initialization error");
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, []);

  const refreshCase = useCallback(async () => {
    try {
      const data = await getCase();
      if (data) setCaseData(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load case");
    }
  }, []);

  const runInvestigation = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    try {
      const result = await postRunInvestigation();
      // Do NOT clear isRunning here: the RunningStage animation calls
      // finishInvestigation() when it completes (~3.5s).
      setCaseData(result);
      setSelectedStep(0);
      setStressLevelState(0);
      setApprovals({});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run investigation");
      // Only clear on error — animation never shows on failure
      setIsRunning(false);
    }
  }, []);

  const finishInvestigation = useCallback(() => {
    setIsRunning(false);
  }, []);

  const resetCase = useCallback(() => {
    setCaseData(null);
    setSelectedStep(0);
    setStressLevelState(0);
    setApprovals({});
  }, []);

  const setStressLevel = useCallback(async (level: number) => {
    setStressLevelState(level);
    try {
      const stressed = await getStressCase(level);
      setCaseData(stressed);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load stress level");
    }
  }, []);

  const approveAction = useCallback(async (actionId: string) => {
    try {
      const result = await postApproveAction(actionId);
      setApprovals((prev) => ({ ...prev, [actionId]: result }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve action");
    }
  }, []);

  return (
    <AppContext.Provider
      value={{
        user,
        intake,
        caseData,
        selectedStep,
        stressLevel,
        isRunning,
        approvals,
        error,
        setSelectedStep,
        setStressLevel,
        runInvestigation,
        finishInvestigation,
        approveAction,
        refreshCase,
        resetCase,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
