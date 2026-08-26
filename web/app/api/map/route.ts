import { NextResponse } from "next/server";
import { dbConfigured, getMapFeatures } from "@/lib/db";
import type { FeatureCollection } from "geojson";

export async function GET(request: Request) {
  if (!(await dbConfigured())) {
    return NextResponse.json({ error: "Database not configured (set DATABASE_URL)" }, { status: 503 });
  }
  const { searchParams } = new URL(request.url);
  const precinct = searchParams.get("precinct");
  const precinctNum = precinct ? parseInt(precinct, 10) : undefined;

  try {
    const rows = await getMapFeatures(precinctNum);
    const fc: FeatureCollection = {
      type: "FeatureCollection",
      features: rows.map((r) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [r.lng, r.lat] },
        properties: {
          uuid: r.uuid,
          title: r.title,
          address: r.address_norm,
          precinct: r.precinct,
          precinct_num: r.precinct_num,
          nypl_item_url: r.nypl_item_url,
          nypl_image_id: r.nypl_image_id,
        },
      })),
    };
    return NextResponse.json(fc);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Database error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
