export type Player = {
  player_id: string;
  seat: number;
  position: string;
  starting_stack: string;
  is_hero?: boolean;
};
export type Hand = {
  hand_id: string;
  small_blind: string;
  big_blind: string;
  hero_cards: string[];
  board: string[];
  players: Player[];
  actions: unknown[];
  [key: string]: unknown;
};
export type Decision = {
  index: number;
  street: string;
  position: string;
  action: string;
  pot: string;
  stack: string;
  to_call: string;
  call_price: string | null;
  street_start_spr: string | null;
  contexts: string[];
};
export type Step = {
  index: number;
  street: string;
  player: string;
  action: string;
  amount_to: string | null;
  added: string;
  refunded: string;
  pot: string;
  pot_before: string;
  remaining: Record<string, string>;
  folded: string[];
  board: string[];
  pending: string[];
};
export type Report = {
  hand_id: string;
  hero_id: string;
  hero_position: string;
  hero_cards: string[];
  hand_class: string;
  timeline: Step[];
  decisions: Decision[];
  pot: string;
  complete: boolean;
  next_player: string | null;
  pots: { amount: string; eligible: string[] }[];
  assumptions: string[];
};
export type Source = {
  id: string;
  document_id: string;
  title: string;
  body: string;
  source: string;
  tags: string[];
  score: number;
};
export type Review = {
  summary: string;
  observations: { text: string; source_ids: string[] }[];
  assumptions: string[];
  alternatives: string[];
  missing_information: string[];
  next_steps: string[];
  mode: string;
  model: string | null;
  latency_ms: number;
  retrieval_backend: string;
  usage: unknown;
  sources: Source[];
};
export type SavedHand = {
  id: string;
  payload: Hand;
  report: Report;
  review: Review | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
};
export type Note = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  source: string;
};
export type Pattern = {
  id: string;
  title: string;
  target_action: string;
  opportunities: number;
  matches: number;
  rate: number | null;
  status: string;
  suggestion: string;
  evidence: { hand_id: string; decision_index: number }[];
};
export type Stats = {
  hands: number;
  demo_hands: number;
  decisions: number;
  patterns: Pattern[];
  limitation: string;
};
export type Similar = {
  hand_id: string;
  score: number;
  cards: string[];
  position: string;
  is_demo: boolean;
};
export type Config = {
  ai_enabled: boolean;
  retrieval: string;
  model: string;
  version: string;
};
