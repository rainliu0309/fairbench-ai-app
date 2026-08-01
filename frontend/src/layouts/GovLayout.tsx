import {
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardCheck,
  Database,
  FileText,
  LayoutDashboard,
  LogOut,
  LockKeyhole,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { LanguageSwitcher } from "../components/common/LanguageSwitcher";
import { sessionStore } from "../store/session";
import { statsApi, taskApi } from "../api/endpoints";

const navItems = [
  { path: "/workspace", key: "home", icon: LayoutDashboard },
  { path: "/datasets", key: "datasets", icon: Database },
  { path: "/tasks", key: "tasks", icon: ClipboardCheck },
  { path: "/dashboard", key: "dashboard", icon: BarChart3 },
  { path: "/reports", key: "reports", icon: FileText },
];

function userInitials(name: string | undefined, fallback: string) {
  if (!name?.trim()) return fallback;
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length > 1) {
    return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  }
  return Array.from(parts[0]).slice(0, 2).join("").toUpperCase();
}

export function GovLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = sessionStore.getUser();
  const initials = userInitials(user?.display_name, t("topbar.avatar"));
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const overview = useQuery({ queryKey: ["stats-overview", "topbar"], queryFn: statsApi.overview });
  const tasks = useQuery({ queryKey: ["tasks", "topbar-alerts"], queryFn: () => taskApi.list() });
  const alertTasks = (tasks.data?.items ?? []).filter((task) => task.metrics && !task.metrics.is_compliant).slice(0, 3);
  const alertCount = alertTasks.length || (overview.data?.failed_sample_count ?? 0);
  const signOut = () => {
    sessionStore.clearAuth();
    navigate("/login", { replace: true });
  };
  return (
    <div className="gov-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-seal" aria-hidden="true">
            FB
          </div>
          <div className="brand-copy">
            <div className="brand-authority">{t("brand.authority")}</div>
            <div className="brand-name">{t("brand.name")}</div>
            <div className="brand-cn">{t("brand.cn")}</div>
          </div>
        </div>
        <div className="sidebar-section-label">{t("nav.navigation")}</div>
        <nav className="side-nav">
          {navItems.map(({ path, key, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              aria-label={t(`nav.${key}`)}
              className={({ isActive }) =>
                `nav-item ${key === "home" ? "workspace-nav-item" : ""} ${isActive ? "active" : ""}`
              }
            >
              <Icon aria-hidden="true" />
              <span>{t(`nav.${key}`)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="system-state">
            <span>
              <i className="state-dot" />
              {t("nav.systemOnline")}
            </span>
            <span className="state-lock">
              <LockKeyhole size={12} />
              {t("nav.archiveMode")}
            </span>
          </div>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-security">{t("topbar.security")}</span>
            <span className="topbar-divider" aria-hidden="true" />
            <span>{t("brand.system")}</span>
            <span className="topbar-system-id">{t("topbar.systemId")}</span>
          </div>
          <div className="topbar-actions">
            <LanguageSwitcher />
            <div className="topbar-popover-wrap">
              <button
                type="button"
                className="icon-button"
                aria-label={t("topbar.notifications")}
                aria-expanded={alertsOpen}
                onClick={() => {
                  setAlertsOpen((open) => !open);
                  setProfileOpen(false);
                }}
              >
              <Bell />
                {alertCount ? <span className="notification-dot" aria-hidden="true" /> : null}
              </button>
              {alertsOpen ? (
                <div className="topbar-popover alert-popover" role="dialog" aria-label={t("topbar.notifications")}>
                  <div className="popover-title"><AlertTriangle />{t("topbar.alertCenter")}</div>
                  {alertTasks.length ? alertTasks.map((task) => (
                    <button type="button" className="alert-item" key={task.id} onClick={() => { setAlertsOpen(false); navigate("/tasks"); }}>
                      <span>{task.algorithm_name}</span>
                    </button>
                  )) : <div className="popover-empty">{t("topbar.noAlerts")}</div>}
                  <button type="button" className="popover-action" onClick={() => { setAlertsOpen(false); navigate("/tasks"); }}>
                    {t("topbar.viewTasks")}
                  </button>
                </div>
              ) : null}
            </div>
            <div className="topbar-popover-wrap">
              <button type="button" className="user-info user-trigger" onClick={() => { setProfileOpen((open) => !open); setAlertsOpen(false); }} aria-expanded={profileOpen}>
                <div className="user-avatar">{initials}</div>
                <div className="user-copy">
                  <div className="user-role">{user?.display_name ?? t("topbar.role")}</div>
                  <div className="user-agency">{t(`roles.${user?.role ?? "regulatory_reviewer"}`)}</div>
                </div>
              </button>
              {profileOpen ? <div className="topbar-popover profile-popover" role="dialog"><div className="profile-name">{user?.display_name}</div><div className="profile-email">{user?.email}</div><div className="profile-role">{t(`roles.${user?.role ?? "regulatory_reviewer"}`)}</div></div> : null}
            </div>
            <button type="button" className="icon-button" onClick={signOut} aria-label={t("auth.signOut")}>
              <LogOut />
            </button>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
