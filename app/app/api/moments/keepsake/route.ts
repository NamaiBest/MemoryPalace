import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";
// Muse Image takes tens of seconds, well past the default route budget.
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await backendFetch("/moments/keepsake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ momentId: body.momentId }),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Meta Muse Image is offline" },
      { status: 503 },
    );
  }
}
