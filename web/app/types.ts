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
