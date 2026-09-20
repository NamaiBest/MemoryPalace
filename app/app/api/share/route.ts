import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await backendFetch("/share/compose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        momentIds: body.momentIds,
        recipient: body.recipient,
        sender: body.sender,
      }),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Meta Muse Spark is offline, so the note cannot be written right now" },
      { status: 503 },
    );
  }
}
