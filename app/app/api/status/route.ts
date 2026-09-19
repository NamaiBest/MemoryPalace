import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET() {
  const startedAt = Date.now();
  try {
    const response = await backendFetch("/status");
    if (!response.ok) {
      return NextResponse.json({
        reachable: false,
        reason: `backend returned HTTP ${response.status}`,
        latencyMs: Date.now() - startedAt,
      });
    }
    const status = await response.json();
    return NextResponse.json({
      reachable: true,
      latencyMs: Date.now() - startedAt,
      checkedAt: new Date().toISOString(),
      ...status,
    });
  } catch (error) {
    // Not running is the normal case outside a session, so this is reported as state
    // rather than thrown — the debug page needs to say "off", not fall over.
    return NextResponse.json({
      reachable: false,
      reason: error instanceof Error ? error.message : "backend unreachable",
      latencyMs: Date.now() - startedAt,
      checkedAt: new Date().toISOString(),
    });
  }
}
