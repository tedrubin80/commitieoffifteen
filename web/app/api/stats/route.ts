import { NextResponse } from "next/server";
import { dbConfigured, getStats } from "@/lib/db";

export async function GET() {
  if (!(await dbConfigured())) {
    return NextResponse.json({ configured: false });
  }
  try {
    const stats = await getStats();
    return NextResponse.json({ configured: true, stats });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json({ configured: true, error: msg }, { status: 500 });
  }
}
