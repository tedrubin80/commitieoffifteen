import { NextResponse } from "next/server";
import { dbConfigured, searchRecords } from "@/lib/db";

export async function GET(request: Request) {
  if (!(await dbConfigured())) {
    return NextResponse.json({ error: "Database not configured (set DATABASE_URL)" }, { status: 503 });
  }
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";
  const precinct = searchParams.get("precinct");
  const precinctNum = precinct ? parseInt(precinct, 10) : undefined;
  const limit = Math.min(parseInt(searchParams.get("limit") || "50", 10), 200);

  try {
    const hits = await searchRecords(q, precinctNum, limit);
    return NextResponse.json({ q, hits, count: hits.length });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
