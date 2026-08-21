export interface PropertyFilters {
  q?: string;
  province?: string;
  city?: string;
  suburb?: string;
  property_type?: string;
  listing_type?: "sale" | "rent" | "";
  contact_status?: string;
  listing_source?: string;
  min_price?: number;
  max_price?: number;
  bedrooms?: number;
  bathrooms?: number;
  min_days_on_market?: number;
  max_days_on_market?: number;
  min_score?: number;
  max_score?: number;
}

export const EMPTY_FILTERS: PropertyFilters = {};

export function filtersToParams(filters: PropertyFilters): Record<string, string> {
  const params: Record<string, string> = {};
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params[key] = String(value);
    }
  });
  return params;
}
