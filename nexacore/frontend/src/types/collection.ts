export interface Source {
  id: string;
  name: string;
  source_key: string;
  collector_type: string;
  is_enabled: boolean;
  disabled_reason: string | null;
  last_successful_scan_at: string | null;
  last_error: string | null;
  listings_collected_count: number;
}

export interface ScanJob {
  id: string;
  source_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  listings_discovered: number;
  new_listings: number;
  updated_listings: number;
  duplicate_listings: number;
  error_count: number;
  errors: string | null;
}
