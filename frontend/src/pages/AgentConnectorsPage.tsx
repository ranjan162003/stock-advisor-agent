import { RefreshCw } from "lucide-react";

import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ConnectorCard } from "../components/connectors/ConnectorCard";
import { PageHeader } from "../components/layout/PageHeader";
import { useProviderConnections } from "../context/ProviderConnectionsContext";

export function AgentConnectorsPage() {
  const { providers, connectedCount } = useProviderConnections();
  const { statuses, isLoading, error, reloadAll } = providers;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Settings"
        title="Agent connectors"
        description="Connect the AI models the advisor can use. Sign in with your browser, paste an API key, or run a model locally — then choose which one gives the advice."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reloadAll()} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? "spin" : undefined} /> Refresh all
          </button>
        }
      />

      {statuses.length > 0 && (
        <div className="connector-summary">
          <strong>{connectedCount}</strong> of {statuses.length} connectors ready
        </div>
      )}
      {error && <ErrorAlert message={error} />}
      {isLoading && statuses.length === 0 && <LoadingSpinner label="Checking connectors…" />}

      <div className="connector-grid">
        {statuses.map((status) => (
          <ConnectorCard key={status.provider_id} status={status} />
        ))}
      </div>
    </div>
  );
}
