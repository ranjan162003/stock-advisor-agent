import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { AssistantProvider } from "./context/AssistantContext";
import { PrintProvider } from "./context/PrintContext";
import { ToastProvider } from "./context/ToastContext";
import { ProviderConnectionsProvider } from "./context/ProviderConnectionsContext";
import { AdvisorPage } from "./pages/AdvisorPage";
import { AgentConnectorsPage } from "./pages/AgentConnectorsPage";
import { AssistantPage } from "./pages/AssistantPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SipPlannerPage } from "./pages/SipPlannerPage";
import { WatchlistPage } from "./pages/WatchlistPage";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <ProviderConnectionsProvider>
          <AssistantProvider>
            <PrintProvider>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="/" element={<AdvisorPage />} />
                  <Route path="/history" element={<HistoryPage />} />
                  <Route path="/history/:recommendationId" element={<HistoryPage />} />
                  <Route path="/watchlist" element={<WatchlistPage />} />
                  <Route path="/planner" element={<SipPlannerPage />} />
                  <Route path="/assistant" element={<AssistantPage />} />
                  <Route path="/connectors" element={<AgentConnectorsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </PrintProvider>
          </AssistantProvider>
        </ProviderConnectionsProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
