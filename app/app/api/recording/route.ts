import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

const ACTIONS = { start: "/recording/start", stop: "/recording/stop" } as const;

/**
 * Start or stop a recording on the phone, from the browser.
 *
 * Useful beyond convenience: it is the only way to confirm the whole chain is live
 * without a terminal. A start that comes back "recording" proves the web app reached the
 * backend, the backend reached the phone, and the phone's camera stream is actually running.
 */
export async function POST(request: Request) {
  let action: string;
  try {
    action = (await request.json())?.action;
  } catch {
    return NextResponse.json({ error: "expected a JSON body" }, { status: 400 });
  }

  if (action !== "start" && action !== "stop") {
    return NextResponse.json({ error: "action must be start or stop" }, { status: 400 });
  }

  try {
    const response = await backendFetch(ACTIONS[action], {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      // The backend's refusals are the useful part — "complete calibration first",
      // "start the camera preview on the phone first" — so pass them straight through.
      return NextResponse.json(
        { error: payload.error ?? `backend returned HTTP ${response.status}` },
        { status: 400 },
      );
    }
    return NextResponse.json({ ok: true, recording: payload });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "backend unreachable" },
      { status: 503 },
    );
  }
}
