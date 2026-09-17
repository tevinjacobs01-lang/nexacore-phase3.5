import { useEffect, useRef, useState, type TouchEvent } from "react";
import { Navigate, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { copyNativeSharedIntake } from "@/lib/shareIntake";

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
import NewLead from "@/pages/NewLead";
import Contacts from "@/pages/Contacts";
import ContactDetail from "@/pages/ContactDetail";
import LeadDetail from "@/pages/LeadDetail";
import Tasks from "@/pages/Tasks";
import FollowUps from "@/pages/FollowUps";
import Templates from "@/pages/Templates";
import CrmDashboard from "@/pages/CrmDashboard";
import PublicLead from "@/pages/PublicLead";
import Discovery from "@/pages/Discovery";
import SavedSearches from "@/pages/SavedSearches";
import Communications from "@/pages/Communications";
import TenantRequirements from "@/pages/TenantRequirements";
import Capture from "@/pages/Capture";
import SocialProspector from "@/pages/SocialProspector";
import Intake from "@/pages/Intake";
import LeadsWorkspace from "@/pages/LeadsWorkspace";

const SIDEBAR_PREFERENCE_KEY = "nexacore_sidebar_expanded";
const EDGE_SWIPE_THRESHOLD = 24;
const SWIPE_DISTANCE_THRESHOLD = 56;

type TouchStart = {
  x: number;
  y: number;
  startedOnInteractiveElement: boolean;
};

function readSidebarPreference() {
  return localStorage.getItem(SIDEBAR_PREFERENCE_KEY) !== "false";
}

function ProtectedRoute() {
  const token = localStorage.getItem("nexacore_token");
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(readSidebarPreference);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const touchStartRef = useRef<TouchStart | null>(null);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    // Android copies only explicit ACTION_SEND material into this same web
    // intake. This remains harmless in browsers, where the native bridge is absent.
    const consumeShare = () => copyNativeSharedIntake().then((hasShare) => {
      if (hasShare) navigate("/intake");
    }).catch(() => undefined);
    consumeShare();
    // ACTION_SEND can reach a singleTask activity already displaying the
    // WebView. Re-check on foreground rather than creating a second route
    // or native processing pipeline.
    const onFocus = () => { void consumeShare(); };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void consumeShare();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [navigate]);

  function setSidebarExpanded(expanded: boolean) {
    setIsSidebarExpanded(expanded);
    localStorage.setItem(SIDEBAR_PREFERENCE_KEY, String(expanded));
  }

  function handleTouchStart(event: TouchEvent<HTMLDivElement>) {
    if (event.touches.length !== 1) {
      touchStartRef.current = null;
      return;
    }

    const touch = event.touches[0];
    const target = event.target as HTMLElement;
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      startedOnInteractiveElement: Boolean(
        target.closest("a, button, input, select, textarea, [role='button'], [contenteditable='true']"),
      ),
    };
  }

  function handleTouchEnd(event: TouchEvent<HTMLDivElement>) {
    const touchStart = touchStartRef.current;
    touchStartRef.current = null;

    if (!touchStart || event.changedTouches.length !== 1 || touchStart.startedOnInteractiveElement) {
      return;
    }

    const touch = event.changedTouches[0];
    const horizontalDistance = touch.clientX - touchStart.x;
    const verticalDistance = touch.clientY - touchStart.y;

    if (
      Math.abs(horizontalDistance) < SWIPE_DISTANCE_THRESHOLD ||
      Math.abs(horizontalDistance) <= Math.abs(verticalDistance)
    ) {
      return;
    }

    if (horizontalDistance < 0 && isSidebarExpanded) {
      setSidebarExpanded(false);
    } else if (
      horizontalDistance > 0 &&
      !isSidebarExpanded &&
      touchStart.x <= EDGE_SWIPE_THRESHOLD
    ) {
      setSidebarExpanded(true);
    }
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div
      className="flex min-h-screen touch-pan-y bg-[#07111f] text-slate-100"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={() => {
        touchStartRef.current = null;
      }}
    >
      <Sidebar
        expanded={isSidebarExpanded}
        onToggle={() => setSidebarExpanded(!isSidebarExpanded)}
        mobileOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {isMobileMenuOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setIsMobileMenuOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/60 lg:hidden"
        />
      )}

      <div className="min-h-screen min-w-0 flex-1 bg-[#07111f]">
        <Header onOpenMenu={() => setIsMobileMenuOpen(true)} />

        <main className="nc-page min-h-[calc(100vh-65px)]">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/properties" element={<Properties />} />

            <Route path="/contacts" element={<Contacts />} />
            <Route path="/contacts/:id" element={<ContactDetail />} />

            <Route path="/leads" element={<LeadsWorkspace />} />
            <Route path="/leads/new" element={<NewLead />} />
            <Route path="/leads/:id" element={<LeadDetail />} />

            <Route path="/tasks" element={<Tasks />} />
            <Route path="/follow-ups" element={<FollowUps />} />

            <Route path="/crm" element={<CrmDashboard />} />

            <Route path="/templates" element={<Templates />} />
            <Route path="/collection" element={<Collection />} />

            <Route path="/discovery" element={<Discovery />} />
            <Route
              path="/discovery/searches"
              element={<SavedSearches />}
            />

            <Route
              path="/communications"
              element={<Communications />}
            />

            <Route
              path="/tenant-requirements"
              element={<TenantRequirements />}
            />

            <Route path="/capture" element={<Capture />} />
            <Route path="/intake" element={<Intake />} />
            <Route path="/social-prospector" element={<SocialProspector />} />

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

      <Route path="/public-lead" element={<PublicLead />} />

      <Route path="/*" element={<ProtectedRoute />} />
    </Routes>
  );
}

