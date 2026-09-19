import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const response = await backendFetch("/moments");
    if (!response.ok) {
      return NextResponse.json(
        { moments: [], error: `backend returned ${response.status}` },
        { status: 502 },
      );
    }
    const body = await response.json();
    return NextResponse.json({ moments: body.moments ?? [] });
  } catch {
    // The backend is a local process that is often simply not running. That is an
    // expected state, not an error worth surfacing — the UI falls back to seed data.
    return NextResponse.json({ moments: [], offline: true });
  }
}
