import { NavLink } from "react-router-dom";
import { logout } from "../../lib/api";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/properties", label: "Properties" },
  { to: "/contacts", label: "Contacts" },
  { to: "/leads", label: "Leads" },
  { to: "/tasks", label: "Tasks" },
  { to: "/follow-ups", label: "Follow-ups" },
  { to: "/crm", label: "CRM Dashboard" },
  { to: "/templates", label: "Templates" },
  { to: "/collection", label: "Collection" },
  { to: "/assistant", label: "AI Assistant" },
  { to: "/reports", label: "Reports" },
  { to: "/settings", label: "Settings" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="text-lg font-semibold text-brand-600 dark:text-brand-500 mb-6">
        NexaCore
      </div>
      <nav className="space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm font-medium ${
                isActive
                  ? "bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-500"
                  : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={() => {
          logout();
          window.location.href = "/login";
        }}
        className="mt-6 w-full rounded-md px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
      >
        Logout
      </button>
    </aside>
  );
}