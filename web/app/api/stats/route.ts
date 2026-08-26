import { NextResponse } from "next/server";
import { dbEnvStatus, getStats } from "@/lib/db";

export async function GET() {
  const env = dbEnvStatus();
  if (!env.configured) {
    return NextResponse.json({ configured: false, keysPresent: env.keysPresent });
  }
  try {
    const stats = await getStats();
    return NextResponse.json({ configured: true, keysPresent: env.keysPresent, stats });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json(
      { configured: true, keysPresent: env.keysPresent, error: msg },
      { status: 500 },
    );
  }
}
