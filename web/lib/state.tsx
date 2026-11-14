"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { CaseData, IntakeData, User, Approval, Night, CaseSource, CaseVersion, UploadResult } from "./types";
import {
  getMe,
  getIntake,
  getCase,
  getCaseVersion,
  getStressCase,
  postRunInvestigation,
  postUploadLogs,
  postApproveAction,
  getApprovals,
} from "./api";

const POLL_MS = 4000;

interface AppContextType {
  user: User | null;
  intake: IntakeData | null;
  caseData: CaseData | null;
  source: CaseSource | null;
  selectedStep: number;
  stressLevel: number;
  isRunning: boolean;
  approvals: Record<string, Approval>;
  error: string | null;
  setSelectedStep: (step: number) => void;
  setStressLevel: (level: number) => Promise<void>;
  night: Night;
  setNight: (night: Night) => void;
  runInvestigation: () => Promise<void>;
  uploadLogs: (file: File) => Promise<UploadResult | null>;
  finishInvestigation: () => void;
  approveAction: (actionId: string) => Promise<void>;
  refreshCase: () => Promise<void>;
  resetCase: () => void;
}

const AppContext = createContext<AppContextType | null>(null);

function approvalMap(list: Approval[]) {
  const map: Record<string, Approval> = {};
  for (const approval of list) {
    map[approval.action_id] = approval;
  }
  return map;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [intake, setIntake] = useState<IntakeData | null>(null);
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [source, setSource] = useState<CaseSource | null>(null);
  const [selectedStep, setSelectedStep] = useState<number>(0);
  const [stressLevel, setStressLevelState] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [approvals, setApprovals] = useState<Record<string, Approval>>({});
  const [error, setError] = useState<string | null>(null);
  const [night, setNight] = useState<Night>("attack");
  const seenVersion = useRef<CaseVersion | null>(null);
  const running = useRef(false);

  useEffect(() => {
    running.current = isRunning;
  }, [isRunning]);

  const rememberVersion = useCallback(async () => {
    const version = await getCaseVersion();
    seenVersion.current = version;
    if (version) setSource(version.source);
  }, []);

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
        setApprovals(approvalMap(approvalsList));

        const currentCase = await getCase();
        if (mounted && currentCase) setCaseData(currentCase);
        if (mounted) await rememberVersion();
      } catch (err: unknown) {
        if (mounted) setError(err instanceof Error ? err.message : "Initialization error");
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [rememberVersion]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    let busy = false;

    async function poll() {
      if (busy || running.current || document.hidden) return;
      busy = true;
      try {
        const next = await getCaseVersion();
        const seen = seenVersion.current;
        if (!active || !next || running.current) return;
        seenVersion.current = next;
        setSource(next.source);
        if (!seen) return;
        if (next.case !== seen.case) {
          const [freshCase, freshIntake, freshApprovals] = await Promise.all([
            getCase(),
            getIntake(),
            getApprovals(),
          ]);
          if (!active || running.current) return;
          setCaseData(freshCase);
          setIntake(freshIntake);
          setApprovals(approvalMap(freshApprovals));
          setSelectedStep(0);
          setStressLevelState(0);
        } else if (next.approvals !== seen.approvals) {
          const freshApprovals = await getApprovals();
          if (active) setApprovals(approvalMap(freshApprovals));
        }
      } catch {
        // The next tick tries again.
      } finally {
        busy = false;
      }
    }

    const timer = window.setInterval(poll, POLL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [user]);

  const refreshCase = useCallback(async () => {
    try {
      const data = await getCase();
      if (data) setCaseData(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load case");
    }
  }, []);

  const restorePrevious = useCallback(async (message: string) => {
    setError(message);
    setIsRunning(false);
    const previous = await getCase();
    if (previous) setCaseData(previous);
  }, []);

  const runInvestigation = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    setCaseData(null);
    try {
      const result = await postRunInvestigation(night);
      setCaseData(result);
      setSelectedStep(0);
      setStressLevelState(0);
      setApprovals({});
      setIntake(await getIntake());
      await rememberVersion();
    } catch (err: unknown) {
      await restorePrevious(err instanceof Error ? err.message : "Failed to run investigation");
    }
  }, [night, rememberVersion, restorePrevious]);

  const uploadLogs = useCallback(
    async (file: File) => {
      setIsRunning(true);
      setError(null);
      setCaseData(null);
      try {
        const result = await postUploadLogs(file);
        const [freshCase, freshIntake] = await Promise.all([getCase(), getIntake()]);
        setCaseData(freshCase);
        setSelectedStep(0);
        setStressLevelState(0);
        setApprovals({});
        setIntake(freshIntake);
        await rememberVersion();
        if (!freshCase) setIsRunning(false);
        return result;
      } catch (err: unknown) {
        await restorePrevious(err instanceof Error ? err.message : "The upload failed");
        return null;
      }
    },
    [rememberVersion, restorePrevious],
  );

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
        source,
        selectedStep,
        stressLevel,
        isRunning,
        approvals,
        error,
        setSelectedStep,
        setStressLevel,
        night,
        setNight,
        runInvestigation,
        uploadLogs,
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
