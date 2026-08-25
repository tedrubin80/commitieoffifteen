import { NextResponse } from "next/server";
import { dbConfigured, getPrecinctStats } from "@/lib/db";

export async function GET() {
  if (!(await dbConfigured())) {
    return NextResponse.json({ error: "POSTGRES_URL not configured" }, { status: 503 });
  }
  try {
    const stats = await getPrecinctStats();
    return NextResponse.json({ precincts: stats });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
