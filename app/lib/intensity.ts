export type IntensityLevel = "critical" | "high" | "moderate" | "weak";

export const INTENSITY = {
  critical: { label: "Critical", color: "#ff5f57", description: "Very high spike" },
  high: { label: "High", color: "#ff9f43", description: "Elevated spike" },
  moderate: { label: "Moderate", color: "#f2d15f", description: "Noticeable spike" },
  weak: { label: "Weak", color: "#64c587", description: "Low spike, kept just in case" },
} satisfies Record<IntensityLevel, { label: string; color: string; description: string }>;

export function intensityLevel(value: number): IntensityLevel {
  if (value >= 0.85) return "critical";
  if (value >= 0.7) return "high";
  if (value >= 0.55) return "moderate";
  return "weak";
}

export function intensityMeta(value: number) {
  const level = intensityLevel(value);
  return { level, ...INTENSITY[level] };
}

