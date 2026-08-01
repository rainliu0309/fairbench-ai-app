import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { GlobalErrorDialog } from "./components/common/GlobalErrorDialog";
import { GovLayout } from "./layouts/GovLayout";
import { authApi } from "./api/endpoints";
import { sessionStore } from "./store/session";
import { Auth } from "./views/Auth";

const AuditReport = lazy(() =>
  import("./views/AuditReport").then((module) => ({ default: module.AuditReport })),
);
const DatasetManage = lazy(() =>
  import("./views/DatasetManage").then((module) => ({
    default: module.DatasetManage,
  })),
);
const FairnessDashboard = lazy(() =>
  import("./views/FairnessDashboard").then((module) => ({
    default: module.FairnessDashboard,
  })),
);
const TaskDashboard = lazy(() =>
  import("./views/TaskDashboard").then((module) => ({
    default: module.TaskDashboard,
  })),
);
const Workspace = lazy(() =>
  import("./views/Workspace").then((module) => ({ default: module.Workspace })),
);

function RequireSession() {
  const { t } = useTranslation();
  const [hasSession, setHasSession] = useState(Boolean(sessionStore.getToken()));
  const identity = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.me,
    enabled: hasSession,
    retry: false,
  });
  useEffect(() => {
    if (identity.isError) {
      sessionStore.clearAuth();
      setHasSession(false);
    }
  }, [identity.isError]);
  // The local demonstration administrator is intentionally created only after
  // the user confirms the pre-filled one-click sign-in on the login page.
  if (!hasSession) return <Navigate to="/login" replace />;
  if (identity.isError) return <Navigate to="/login" replace />;
  if (identity.isLoading) return <div className="route-loading">{t("auth.loadingWorkspace")}</div>;
  return <Outlet />;
}

/**
 * A fresh browser session starts at the workspace overview. In-app navigation
 * remains untouched so auditors can move freely through every workflow view.
 */
function StartAtWorkspace() {
  const location = useLocation();
  const shouldResolveEntry = useRef(true);

  if (shouldResolveEntry.current) {
    shouldResolveEntry.current = false;
    if (location.pathname !== "/workspace") {
      return <Navigate to="/workspace" replace />;
    }
  }

  return <Outlet />;
}

export default function App() {
  const { t } = useTranslation();
  return (
    <>
      <Suspense fallback={<div className="route-loading">{t("common.loading")}</div>}>
        <Routes>
          <Route path="/login" element={<Auth />} />
          <Route element={<RequireSession />}>
            <Route element={<StartAtWorkspace />}>
              <Route element={<GovLayout />}>
                <Route index element={<Navigate to="/workspace" replace />} />
                <Route path="/workspace" element={<Workspace />} />
                <Route path="/datasets" element={<DatasetManage />} />
                <Route path="/tasks" element={<TaskDashboard />} />
                <Route path="/dashboard" element={<FairnessDashboard />} />
                <Route path="/reports" element={<AuditReport />} />
                <Route path="*" element={<Navigate to="/workspace" replace />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </Suspense>
      <GlobalErrorDialog />
    </>
  );
}
