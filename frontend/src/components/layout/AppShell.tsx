import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";

import { AppSidebar } from "./AppSidebar";

/** Sidebar + main content area. On narrow screens the sidebar becomes a slide-in drawer. */
export function AppShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <AppSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      {isSidebarOpen && <div className="app-shell__scrim" onClick={() => setIsSidebarOpen(false)} />}

      <div className="app-shell__main">
        <header className="mobile-topbar">
          <button
            type="button"
            className="icon-button"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <span className="mobile-topbar__title">Stock Advisor</span>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
