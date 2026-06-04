export function elixirColor(e: number | null): string {
  return e == null ? "#6b7280" : "#c026d3";
}

export function scoreColor(s: number): string {
  if (s >= 85) return "#22c55e";
  if (s >= 65) return "#eab308";
  return "#ef4444";
}

export function severityColor(sev: string): string {
  if (sev === "high") return "#ef4444";
  if (sev === "medium") return "#f59e0b";
  return "#3b82f6";
}

export function roleColor(role: string | null): string {
  switch (role) {
    case "win-condition":
      return "#f59e0b";
    case "spell":
      return "#a855f7";
    case "building":
      return "#38bdf8";
    case "anti-air":
      return "#22c55e";
    default:
      return "#94a3b8";
  }
}
