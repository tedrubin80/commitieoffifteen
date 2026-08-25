export type PrecinctStat = {
  precinct: string;
  precinct_num: number | null;
  count: number;
};

export type GeoFeature = {
  uuid: string;
  title: string;
  address_norm: string | null;
  precinct: string | null;
  precinct_num: number | null;
  nypl_image_id: string | null;
  nypl_item_url: string | null;
  lat: number;
  lng: number;
  geo_status: string | null;
};

export type CofRecord = {
  uuid: string;
  title: string;
  address_norm: string | null;
  title_kind: string | null;
  precinct: string | null;
  precinct_num: number | null;
  date_start: number | null;
  date_end: number | null;
  nypl_image_id: string | null;
  nypl_item_url: string | null;
  genres: string[] | null;
  host_chain: string | null;
  lat: number | null;
  lng: number | null;
  geo_status: string | null;
  geo_source: string | null;
  ocr_text: string | null;
  char_count: number | null;
  ocr_quality: string | null;
};

export type SearchHit = {
  uuid: string;
  title: string;
  precinct: string | null;
  address_norm: string | null;
  snippet: string | null;
  rank?: number;
};
