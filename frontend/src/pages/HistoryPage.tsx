import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { recommendationApi } from "../api/recommendationApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { RecommendationHistoryList } from "../components/history/RecommendationHistoryList";
import { PageHeader } from "../components/layout/PageHeader";
import { RecommendationResults } from "../components/recommendation/RecommendationResults";
import type { RecommendationHistoryItem, RecommendationResponse } from "../types/recommendation.types";

export function HistoryPage() {
  const { recommendationId } = useParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<RecommendationHistoryItem[] | null>(null);
  const [selected, setSelected] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      setItems(await recommendationApi.listHistory());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  // Open the most recent one by default.
  useEffect(() => {
    if (!recommendationId && items && items.length > 0) navigate(`/history/${items[0].id}`, { replace: true });
  }, [recommendationId, items, navigate]);

  useEffect(() => {
    if (!recommendationId) return setSelected(null);
    setSelected(null);
    recommendationApi
      .getById(Number(recommendationId))
      .then(setSelected)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [recommendationId]);

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this recommendation from history?")) return;
    try {
      await recommendationApi.remove(id);
      if (Number(recommendationId) === id) navigate("/history", { replace: true });
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="page">
      <PageHeader
        eyebrow="Track record"
        title="History"
        description="Every recommendation is saved exactly as it was shown, so you can compare them over time."
      />
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {items === null ? (
        <LoadingSpinner />
      ) : items.length === 0 ? (
        <section className="card empty-state">
          <p>No recommendations yet.</p>
          <Link to="/" className="button button--primary">
            Get your first recommendation
          </Link>
        </section>
      ) : (
        <div className="history-layout">
          <aside className="card history-layout__list">
            <RecommendationHistoryList items={items} onDelete={handleDelete} />
          </aside>
          <div className="history-layout__detail">
            {selected ? <RecommendationResults recommendation={selected} /> : <LoadingSpinner />}
          </div>
        </div>
      )}
    </div>
  );
}
