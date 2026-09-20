import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";
// Muse Spark reads the whole day before a word is sent, so this outlives a chat turn.
export const maxDuration = 300;

/** The favourite recipients, read from the backend so no address lives in the source. */
export async function GET() {
  try {
    const response = await backendFetch("/status");
    if (!response.ok) throw new Error("backend unavailable");
    const body = await response.json();
    return NextResponse.json({ contacts: body.digest?.contacts ?? [] });
  } catch {
    return NextResponse.json({ contacts: [] });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const response = await backendFetch("/digest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: body.date ?? null,
        send: Boolean(body.send),
        force: true,
        to: body.to,
        days: body.days,
        momentIds: body.momentIds,
        attach: body.attach,
      }),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "The digest service is offline" },
      { status: 503 },
    );
  }
}
