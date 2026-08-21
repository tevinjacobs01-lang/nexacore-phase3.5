import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Property } from "@/types/property";
import { EMPTY_FILTERS, filtersToParams, type PropertyFilters } from "@/types/filters";
import FiltersSidebar from "@/components/properties/FiltersSidebar";

async function markActivity(propertyId: string, activityType: string) {
  await api.post(`/properties/${propertyId}/activities`, { activity_type: activityType });
}

export default function Properties() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [filters, setFilters] = useState<PropertyFilters>(EMPTY_FILTERS);
  const [search, setSearch] = useState("");

  function fetchProperties() {
    const params = { ...filtersToParams(filters), ...(search ? { q: search } : {}) };
    api
      .get<Property[]>("/properties/", { params })
      .then((res) => setProperties(res.data))
      .catch(() => setProperties([]));
  }

  useEffect(() => {
    fetchProperties();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, search]);

  async function handleContacted(id: string) {
    await markActivity(id, "contacted");
    fetchProperties();
  }

  async function handleCreateLead(propertyId: string) {
    try {
      await api.post("/leads/", {
        property_id: propertyId,
        priority: "medium",
      });
      alert("Lead created successfully.");
    } catch (error) {
      console.error(error);
      alert("Could not create lead.");
    }
  }


  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Properties</h2>
        <input
          type="text"
          placeholder="Search address, suburb, reference, agent, phoneâ€¦"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-80 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
        />
      </div>

      <div className="flex gap-4">
        <FiltersSidebar filters={filters} onChange={setFilters} onClear={() => setFilters(EMPTY_FILTERS)} />

        <div className="flex-1 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 text-left">Address</th>
                <th className="px-4 py-2 text-left">Suburb</th>
                <th className="px-4 py-2 text-left">Price</th>
                <th className="px-4 py-2 text-left">DOM</th>
                <th className="px-4 py-2 text-left">Score</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {properties.map((p) => (
                <tr key={p.id} className="bg-white dark:bg-gray-950">
                  <td className="px-4 py-2">{p.address ?? "â€“"}</td>
                  <td className="px-4 py-2">{p.suburb ?? "â€“"}</td>
                  <td className="px-4 py-2">
                    {p.asking_price ? `R${p.asking_price.toLocaleString()}` : "â€“"}
                  </td>
                  <td className="px-4 py-2">{p.days_on_market ?? "â€“"}</td>
                  <td className="px-4 py-2">
                    <span
                      className={
                        p.lead_score >= 70
                          ? "text-red-600 font-medium"
                          : p.lead_score >= 40
                          ? "text-amber-600 font-medium"
                          : "text-gray-500"
                      }
                    >
                      {p.lead_score}
                    </span>
                  </td>
                  <td className="px-4 py-2">{p.contact_status}</td>
                  <td className="px-4 py-2">
                    {p.contact_status === "not_contacted" && (
                      <button
                        onClick={() => handleContacted(p.id)}
                        className="text-xs text-brand-600 dark:text-brand-500 hover:underline"
                      >
                        Mark Contacted
                      </button>
                    )}
                    <button
                      onClick={() => handleCreateLead(p.id)}
                      className="ml-3 text-xs text-brand-600 dark:text-brand-500 hover:underline"
                    >
                      Create Lead
                    </button>
                  </td>
                </tr>
              ))}
              {properties.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-gray-400">
                    No properties match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}




