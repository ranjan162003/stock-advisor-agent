import { Calculator, History, LineChart, Plug, ShieldAlert, Sparkles, Star, X, type LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useProviderConnections } from "../../context/ProviderConnectionsContext";
import { Skeleton } from "../common/Skeleton";
import { ProviderLogo } from "../connectors/ProviderLogo";
import { ThemeToggle } from "./ThemeToggle";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Invest",
    items: [
      { to: "/", label: "Advisor", icon: LineChart, end: true },
      { to: "/history", label: "History", icon: History },
      { to: "/watchlist", label: "Watchlist", icon: Star },
    ],
  },
  {
    title: "Plan",
    items: [
      { to: "/planner", label: "SIP planner", icon: Calculator },
      { to: "/assistant", label: "Ask AI", icon: Sparkles },
    ],
  },
  {
    title: "Settings",
    items: [{ to: "/connectors", label: "Agent connectors", icon: Plug }],
  },
];

interface AppSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AppSidebar({ isOpen, onClose }: AppSidebarProps) {
  const { activeStatus, activeModel, connectedCount, providers } = useProviderConnections();
  const totalProviders = providers.statuses.length;

  return (
    <aside className={`sidebar${isOpen ? " sidebar--open" : ""}`} aria-label="Main navigation">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden="true">₹</span>
        <div>
          <div className="sidebar__product">Stock Advisor</div>
          <div className="sidebar__tagline">AI allocation agent</div>
        </div>
        <button type="button" className="icon-button sidebar__close" onClick={onClose} aria-label="Close menu">
          <X size={18} />
        </button>
      </div>

      <nav className="sidebar__nav">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="sidebar__section">
            <div className="sidebar__section-title">{section.title}</div>
            <ul>
              {section.items.map(({ to, label, icon: Icon, end }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    end={end}
                    onClick={onClose}
                    className={({ isActive }) => `sidebar__link${isActive ? " sidebar__link--active" : ""}`}
                  >
                    <Icon size={18} />
                    <span>{label}</span>
                    {to === "/connectors" && totalProviders > 0 && (
                      <span className="sidebar__count" title="Connected providers">
                        {connectedCount}/{totalProviders}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="sidebar__footer">
        <ThemeToggle />
        <NavLink to="/connectors" onClick={onClose} className="active-model-chip">
          {activeStatus ? (
            <>
              <ProviderLogo providerId={activeStatus.provider_id} size={30} />
              <div className="active-model-chip__text">
                <span className="active-model-chip__label">Advising with</span>
                <span className="active-model-chip__name">
                  {activeStatus.display_name}
                  <span className="muted"> · {activeModel || activeStatus.default_model}</span>
                </span>
              </div>
              <span
                className={`status-dot${activeStatus.is_ready ? " status-dot--good" : " status-dot--off"}`}
                title={activeStatus.is_ready ? "Connected" : "Not connected"}
              />
            </>
          ) : (
            <span className="active-model-chip__loading" role="status" aria-label="Checking connectors">
              <Skeleton width={30} height={30} radius={8} className="skeleton-block--on-dark" />
              <span className="active-model-chip__text">
                <Skeleton width={70} height={9} className="skeleton-block--on-dark" />
                <Skeleton width={130} height={12} className="skeleton-block--on-dark" />
              </span>
            </span>
          )}
        </NavLink>
        <p className="sidebar__disclaimer">
          <ShieldAlert size={14} aria-hidden="true" /> Educational use only — not financial advice.
        </p>
      </div>
    </aside>
  );
}
