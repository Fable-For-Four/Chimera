// TypeScript types representing the data contracts defined in PLAN.md §4 and §14

export type Night = "attack" | "quiet" | "random";

export interface User {
  id: number;
  email: string;
  name: string;
  role: "viewer" | "analyst" | "admin";
  verified: boolean;
}

export interface IntakeSummary {
  events: number;
  sources: number;
  late: number;
  alerts_fired: number;
}

export interface AlertRule {
  name: string;
  seen: string;
  ratio: number;
  fired: boolean;
}

export interface VolumePoint {
  start: string;
  count: number;
}

export interface RawEventLine {
  id: string;
  time: string;
  source: string;
  raw: string;
}

export interface IntakeData {
  summary: IntakeSummary;
  alert_rules: AlertRule[];
  volume: VolumePoint[];
  latest: RawEventLine[];
}

export interface PipelineStage {
  name: string;
  does: string;
  result: string;
  seconds: number;
}

export interface EntryPoint {
  account: string;
  event: string;
  text: string;
}

export interface BlastRadius {
  accounts: string[];
  touched: string[];
  reachable: string[];
}

export interface DataAtRisk {
  files: number;
  bytes_out: number;
}

export interface Verdict {
  label: string;
  confidence: number;
  found: boolean;
  headline: string;
  entry_point?: EntryPoint;
  blast_radius?: BlastRadius;
  data_at_risk?: DataAtRisk;
  weakest_step?: number;
}

export interface Signal {
  name: string;
  weight: number;
}

export interface Exhibit {
  id: string;
  raw: string;
  late: boolean;
  present: boolean;
}

export interface ChainStep {
  step: number;
  stage: string;
  technique: string;
  time: string;
  minute: number;
  from: string;
  to: string;
  what: string;
  confidence: number;
  inferred: boolean;
  usual: string;
  now: string;
  signals: Signal[];
  exhibits: Exhibit[];
}

export interface GraphNode {
  id: string;
  type: "user" | "machine" | "outside";
  state: "hit" | "reach" | "normal";
  x: number;
  y: number;
  step?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Hypothesis {
  name: string;
  share: number;
  fits: string[];
  breaks: string[];
}

export interface ForensicEvent {
  id: string;
  time: string;
  source: string;
  raw: string;
  score: number;
  reasons: string[];
  step: number | null;
  late: boolean;
  truth: "found" | "missed" | "false_link" | null;
}

export interface TruthScore {
  planted: number;
  found: number;
  linked: number;
  recall: number;
  precision: number;
  missed: string[];
  false_links: string[];
}

export interface ReportSentence {
  text: string;
  cites: string[];
  step: number;
}

export interface ActionItem {
  id: string;
  kind: "Contain" | "Check";
  text: string;
}

export interface QuestionCite {
  id: string;
  step: number;
}

export interface QuestionItem {
  q: string;
  a: string;
  cites: QuestionCite[];
}

export interface CaseData {
  level: number;
  deleted: number;
  summary: IntakeSummary;
  stages: PipelineStage[];
  verdict: Verdict;
  chain: ChainStep[];
  graph: GraphData;
  volume: VolumePoint[];
  hypotheses: Hypothesis[];
  events: ForensicEvent[];
  truth_score: TruthScore;
  report: ReportSentence[];
  limits: string[];
  actions: ActionItem[];
  questions: QuestionItem[];
}

export interface Approval {
  action_id: string;
  approved_by: string;
  approved_at: string;
}
