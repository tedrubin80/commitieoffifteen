import { NextResponse } from "next/server";
import { dbConfigured, getRecord, nyplImageUrl } from "@/lib/db";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ uuid: string }> },
) {
  if (!(await dbConfigured())) {
    return NextResponse.json({ error: "Database not configured (set DATABASE_URL)" }, { status: 503 });
  }
  const { uuid } = await params;
  try {
    const record = await getRecord(uuid);
    if (!record) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({
      ...record,
      nypl_image_url: nyplImageUrl(record.nypl_image_id),
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
