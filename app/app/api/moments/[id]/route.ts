import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

const MOMENT_ID = /^capture-[0-9a-f]{8}$/;

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!MOMENT_ID.test(id)) {
    return NextResponse.json({ error: "invalid moment id" }, { status: 400 });
  }
  try {
    const response = await backendFetch(`/moments/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    const body = await response.json().catch(() => ({}));
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json({ error: "Memory library is offline" }, { status: 503 });
  }
}
