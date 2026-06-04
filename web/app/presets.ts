export interface Preset {
  name: string;
  cards: string[];
}

export const PRESETS: Preset[] = [
  {
    name: "2.6 Hog Cycle",
    cards: ["hog-rider", "musketeer", "ice-golem", "ice-spirit", "skeletons", "cannon", "fireball", "the-log"],
  },
  {
    name: "Lavaloon",
    cards: ["lava-hound", "balloon", "mega-minion", "minions", "tombstone", "fireball", "zap", "skeleton-dragons"],
  },
  {
    name: "Golem Beatdown",
    cards: ["golem", "night-witch", "baby-dragon", "mega-minion", "lightning", "tornado", "barbarian-barrel", "elixir-collector"],
  },
];
