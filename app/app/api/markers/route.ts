import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

const LABELS = new Set([
  "calibration_start", "calibration_end", "oddball_standard", "oddball_target",
]);

/**
 * Forward a stimulus marker to the backend so it lands in events.jsonl beside the EEG.
 *
 * Timing matters more than the reply: the calibration task fires this at each stimulus
 * onset and must not wait on it. The route therefore validates cheaply and forwards
 * once; the caller treats the request as fire-and-forget.
 */
export async function POST(request: Request) {
  let body: { label?: string; detail?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "expected a JSON body" }, { status: 400 });
  }
  if (!body.label || !LABELS.has(body.label)) {
    return NextResponse.json({ error: "unsupported marker label" }, { status: 400 });
  }

  try {
    const response = await backendFetch("/markers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: body.label, detail: body.detail ?? {} }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json({ error: payload.error ?? `backend ${response.status}` }, { status: 400 });
    }
    return NextResponse.json({ ok: true, marker: payload });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "backend unreachable" },
      { status: 503 },
    );
  }
}
