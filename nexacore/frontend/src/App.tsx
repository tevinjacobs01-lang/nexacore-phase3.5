import { Navigate, Routes, Route } from "react-router-dom";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import Dashboard from "@/pages/Dashboard";
import Properties from "@/pages/Properties";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Settings from "@/pages/Settings";
import Assistant from "@/pages/Assistant";
import Reports from "@/pages/Reports";
import Collection from "@/pages/Collection";
import Leads from "@/pages/Leads";
import Contacts from "@/pages/Contacts";
import ContactDetail from "@/pages/ContactDetail";
import LeadDetail from "@/pages/LeadDetail";
import Tasks from "@/pages/Tasks";
import FollowUps from "@/pages/FollowUps";
import Templates from "@/pages/Templates";
import CrmDashboard from "@/pages/CrmDashboard";

function ProtectedRoute() {
  const token = localStorage.getItem("nexacore_token");

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <div className="flex-1">
        <Header />

        <main className="p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/properties" element={<Properties />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/contacts/:id" element={<ContactDetail />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/leads/:id" element={<LeadDetail />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/follow-ups" element={<FollowUps />} />
            <Route path="/crm" element={<CrmDashboard />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/*" element={<ProtectedRoute />} />
    </Routes>
  );
}