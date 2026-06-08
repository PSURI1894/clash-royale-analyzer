export interface CardSummary {
  key: string;
  name: string;
  elixir: number | null;
  type: string | null;
  rarity: string | null;
  arena: number | null;
}

export interface AnalyzerCardOut {
  key: string;
  name: string;
  elixir: number | null;
  type: string | null;
  rarity: string | null;
  dps: number | null;
  count: number;
  targets_air: boolean;
  targets_ground: boolean;
  targets_buildings_only: boolean;
  is_flying: boolean;
  role: string | null;
}

export interface DeckMetrics {
  card_count: number;
  avg_elixir: number;
  cycle_cost: number;
  elixir_curve: Record<string, number>;
  troop_count: number;
  building_count: number;
  spell_count: number;
  ground_dps: number;
  air_dps: number;
  anti_air_cards: string[];
  air_offense_cards: string[];
  has_small_spell: boolean;
  has_big_spell: boolean;
  has_building: boolean;
}

export interface Archetype {
  primary: string;
  confidence: number;
  signals: string[];
}

export interface Vulnerability {
  code: string;
  severity: string;
  title: string;
  detail: string;
}

export interface AnalysisReport {
  cards: AnalyzerCardOut[];
  win_conditions: string[];
  archetype: Archetype;
  metrics: DeckMetrics;
  vulnerabilities: Vulnerability[];
  stability_score: number;
  weak_against: string[];
}

export interface ResolvedEdge {
  source_key: string;
  target_key: string;
  relation: string;
  value: number;
  confidence: number;
  sources: string[];
}

export interface CardRelations {
  key: string;
  counters: ResolvedEdge[];
  countered_by: ResolvedEdge[];
  synergies: ResolvedEdge[];
}

export interface ThreatCoverage {
  threat: string;
  severity: number;
  coverage: number;
  best_answer: string | null;
  answers: string[];
}

export interface MatchupReport {
  opponent: string;
  score: number;
  verdict: string;
  threats: ThreatCoverage[];
  danger: string[];
}

export interface MiningStats {
  battles: number;
  by_dataset: Record<string, number>;
  mined_edges: number;
  players: number;
}

export interface CardMeta {
  key: string;
  name: string;
  games: number;
  win_rate: number;
  usage: number;
}

export interface Placement {
  card: string;
  note: string;
}

export interface Grounding {
  ok: boolean;
  engine: string;
  unverified_numbers: string[];
}

export interface AdviceSource {
  id: string;
  title: string;
  score: number;
}

export interface AdviceReport {
  deck_archetype: string;
  opponent: string;
  verdict: string;
  key_facts: string[];
  game_plan: string[];
  defensive_routine: string[];
  placements: Placement[];
  citations: string[];
  sources: AdviceSource[];
  grounding: Grounding;
}

export interface SimTower {
  side: string;
  kind: string;
  x: number;
  y: number;
  hp: number;
  max_hp: number;
  alive: boolean;
}

export interface SimUnit {
  name: string;
  side: string;
  x: number;
  y: number;
  hp_pct: number;
}

export interface SimResult {
  winner: string;
  duration: number;
  summary: string;
  attacker_survivors: string[];
  defender_survivors: string[];
  defender_tower_damage: number;
  towers: SimTower[];
  units: SimUnit[];
  events: { t: number; text: string }[];
  warnings: string[];
}

export interface SavedDeck {
  id: number;
  name: string;
  cards: string[];
}
