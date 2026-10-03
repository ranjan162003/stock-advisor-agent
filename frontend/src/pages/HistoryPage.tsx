import { History as HistoryIcon, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { recommendationApi } from "../api/recommendationApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { SkeletonList, SkeletonResults } from "../components/common/Skeleton";
import { RecommendationHistoryList } from "../components/history/RecommendationHistoryList";
import { PageHeader } from "../components/layout/PageHeader";
import { RecommendationResults } from "../components/recommendation/RecommendationResults";
import { useAssistantPageContext } from "../context/AssistantContext";
import { useUndoableDelete } from "../context/ToastContext";
import type { RecommendationHistoryItem, RecommendationResponse } from "../types/recommendation.types";
import { formatInr } from "../utils/displayFormatters";

export function HistoryPage() {
  const { recommendationId } = useParams();
  const navigate = useNavigate();
  const deleteWithUndo = useUndoableDelete();
  const [items, setItems] = useState<RecommendationHistoryItem[] | null>(null);
  const [selected, setSelected] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useAssistantPageContext("history", selected?.id);

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

  const handleDelete = (id: number) => {
    const item = items?.find((i) => i.id === id);
    if (!item || !items) return;
    const position = items.indexOf(item);
    deleteWithUndo({
      message: `Deleted the ${formatInr(item.amount)} recommendation`,
      hide: () => {
        setItems((current) => current?.filter((i) => i.id !== id) ?? null);
        if (Number(recommendationId) === id) navigate("/history", { replace: true });
      },
      restore: () =>
        setItems((current) => {
          if (!current || current.some((i) => i.id === id)) return current;
          const next = [...current];
          next.splice(Math.min(position, next.length), 0, item);
          return next;
        }),
      commit: () => recommendationApi.remove(id),
    });
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
        <div className="history-layout">
          <aside className="card history-layout__list">
            <SkeletonList rows={5} label="Loading your history" />
          </aside>
          <SkeletonResults label="Loading recommendation" />
        </div>
      ) : items.length === 0 ? (
        <section className="card">
          <EmptyState
            icon={HistoryIcon}
            title="No recommendations yet"
            description="Each recommendation you get is saved here — with its reasoning, and how it has done since."
            actions={
              <Link to="/" className="button button--primary">
                <Sparkles size={16} /> Get your first recommendation
              </Link>
            }
          />
        </section>
      ) : (
        <div className="history-layout">
          <aside className="card history-layout__list">
            <RecommendationHistoryList items={items} onDelete={handleDelete} />
          </aside>
          <div className="history-layout__detail">
            {selected ? (
              <RecommendationResults recommendation={selected} showPerformance />
            ) : (
              <SkeletonResults label="Loading recommendation" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
