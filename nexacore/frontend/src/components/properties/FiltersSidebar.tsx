import type { PropertyFilters } from "@/types/filters";

interface Props {
  filters: PropertyFilters;
  onChange: (filters: PropertyFilters) => void;
  onClear: () => void;
}

function TextField({
  label, value, onChange,
}: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
      />
    </div>
  );
}

function NumberRange({
  label, min, max, onMinChange, onMaxChange,
}: {
  label: string; min?: number; max?: number;
  onMinChange: (v?: number) => void; onMaxChange: (v?: number) => void;
}) {
  const parse = (s: string) => (s === "" ? undefined : Number(s));
  return (
    <div className="mb-3">
      <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{label}</label>
      <div className="flex gap-2">
        <input
          type="number"
          placeholder="Min"
          value={min ?? ""}
          onChange={(e) => onMinChange(parse(e.target.value))}
          className="w-1/2 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Max"
          value={max ?? ""}
          onChange={(e) => onMaxChange(parse(e.target.value))}
          className="w-1/2 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
        />
      </div>
    </div>
  );
}

export default function FiltersSidebar({ filters, onChange, onClear }: Props) {
  const set = <K extends keyof PropertyFilters>(key: K, value: PropertyFilters[K]) =>
    onChange({ ...filters, [key]: value });

  return (
    <div className="w-64 shrink-0 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-300">Filters</h3>
        <button onClick={onClear} className="text-xs text-brand-600 dark:text-brand-500 hover:underline">
          Clear all
        </button>
      </div>

      <TextField label="Province" value={filters.province ?? ""} onChange={(v) => set("province", v)} />
      <TextField label="City" value={filters.city ?? ""} onChange={(v) => set("city", v)} />
      <TextField label="Suburb" value={filters.suburb ?? ""} onChange={(v) => set("suburb", v)} />
      <TextField label="Property Type" value={filters.property_type ?? ""} onChange={(v) => set("property_type", v)} />

      <div className="mb-3">
        <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Sale / Rent</label>
        <select
          value={filters.listing_type ?? ""}
          onChange={(e) => set("listing_type", e.target.value as PropertyFilters["listing_type"])}
          className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
        >
          <option value="">Any</option>
          <option value="sale">Sale</option>
          <option value="rent">Rent</option>
        </select>
      </div>

      <NumberRange
        label="Price Range"
        min={filters.min_price} max={filters.max_price}
        onMinChange={(v) => set("min_price", v)} onMaxChange={(v) => set("max_price", v)}
      />
      <NumberRange
        label="Bedrooms / Bathrooms"
        min={filters.bedrooms} max={filters.bathrooms}
        onMinChange={(v) => set("bedrooms", v)} onMaxChange={(v) => set("bathrooms", v)}
      />
      <NumberRange
        label="Days on Market"
        min={filters.min_days_on_market} max={filters.max_days_on_market}
        onMinChange={(v) => set("min_days_on_market", v)} onMaxChange={(v) => set("max_days_on_market", v)}
      />
      <NumberRange
        label="Lead Score"
        min={filters.min_score} max={filters.max_score}
        onMinChange={(v) => set("min_score", v)} onMaxChange={(v) => set("max_score", v)}
      />

      <div className="mb-1">
        <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Contact Status</label>
        <select
          value={filters.contact_status ?? ""}
          onChange={(e) => set("contact_status", e.target.value)}
          className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
        >
          <option value="">Any</option>
          <option value="not_contacted">Not Contacted</option>
          <option value="contacted">Contacted</option>
          <option value="interested">Interested</option>
          <option value="not_interested">Not Interested</option>
          <option value="archived">Archived</option>
        </select>
      </div>
    </div>
  );
}
