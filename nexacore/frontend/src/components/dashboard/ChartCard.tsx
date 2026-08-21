import { ReactNode } from "react";

export default function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">{title}</h3>
      {children}
    </div>
  );
}
