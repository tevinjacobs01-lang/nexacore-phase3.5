import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ChartCard from "@/components/dashboard/ChartCard";
import BarChartWidget from "@/components/dashboard/BarChartWidget";
import NotificationsPanel from "@/components/dashboard/NotificationsPanel";

interface Summary {
  total_listings: number;
  new_listings_today: number;
  hot_leads: number;
  warm_leads: number;
  follow_ups_due_today: number;
  recently_contacted: number;
}

const CARDS: { key: keyof Summary; label: string }[] = [
  { key: "total_listings", label: "Total Listings" },
  { key: "new_listings_today", label: "New Listings Today" },
  { key: "hot_leads", label: "Hot Leads" },
  { key: "warm_leads", label: "Warm Leads" },
  { key: "follow_ups_due_today", label: "Follow-ups Due Today" },
  { key: "recently_contacted", label: "Recently Contacted" },
];

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [bySuburb, setBySuburb] = useState<any[]>([]);
  const [byPriceRange, setByPriceRange] = useState<any[]>([]);
  const [byPropertyType, setByPropertyType] = useState<any[]>([]);
  const [scoreDistribution, setScoreDistribution] = useState<any[]>([]);

  useEffect(() => {
    api.get("/dashboard/summary").then((res) => setSummary(res.data)).catch(() => setSummary(null));
    api.get("/dashboard/charts/by-suburb").then((res) => setBySuburb(res.data)).catch(() => {});
    api.get("/dashboard/charts/by-price-range").then((res) => setByPriceRange(res.data)).catch(() => {});
    api.get("/dashboard/charts/by-property-type").then((res) => setByPropertyType(res.data)).catch(() => {});
    api.get("/dashboard/charts/score-distribution").then((res) => setScoreDistribution(res.data)).catch(() => {});
  }, []);

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Dashboard</h2>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        {CARDS.map((card) => (
          <div
            key={card.key}
            className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
          >
            <div className="text-xs text-gray-500 dark:text-gray-400">{card.label}</div>
            <div className="mt-1 text-xl font-semibold text-gray-900 dark:text-gray-50">
              {summary ? summary[card.key] : "–"}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <ChartCard title="Listings by Suburb">
          <BarChartWidget data={bySuburb} xKey="suburb" yKey="count" />
        </ChartCard>
        <ChartCard title="Listings by Price Range">
          <BarChartWidget data={byPriceRange} xKey="range" yKey="count" color="#22c55e" />
        </ChartCard>
        <ChartCard title="Listings by Property Type">
          <BarChartWidget data={byPropertyType} xKey="property_type" yKey="count" color="#f59e0b" />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ChartCard title="Lead Score Distribution">
            <BarChartWidget data={scoreDistribution} xKey="range" yKey="count" color="#ef4444" />
          </ChartCard>
        </div>
        <NotificationsPanel />
      </div>
    </div>
  );
}
