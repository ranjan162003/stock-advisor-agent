import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { recommendationApi } from "../../api/recommendationApi";
import type { RecommendationHistoryItem } from "../../types/recommendation.types";
import { formatDateTime, formatInr, shortTicker } from "../../utils/displayFormatters";
import { ASSET_MIX_LABELS } from "../../utils/investmentLabels";

interface RecommendationPickerProps {
  id: string;
  label: string;
  value: number | null;
  onChange: (recommendationId: number | null) => void;
}

/** Dropdown of saved recommendations; picks the newest one by default. */
export function RecommendationPicker({ id, label, value, onChange }: RecommendationPickerProps) {
  const [items, setItems] = useState<RecommendationHistoryItem[] | null>(null);

  useEffect(() => {
    recommendationApi
      .listHistory(30)
      .then((history) => {
        setItems(history);
        if (value === null && history.length > 0) onChange(history[0].id);
      })
      .catch(() => setItems([]));
    // Load once; `value` changes are driven by the user afterwards.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (items === null) return <p className="muted">Loading your recommendations…</p>;
  if (items.length === 0) {
    return (
      <p className="field__hint field__hint--warning">
        No saved recommendations yet — <Link to="/">get one on the Advisor page</Link> first.
      </p>
    );
  }

  return (
    <label className="field" htmlFor={id}>
      <span className="field__label">{label}</span>
      <select
        id={id}
        className="input"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
      >
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            #{item.id} · {formatInr(item.amount)} · {ASSET_MIX_LABELS[item.asset_mix ?? "stocks"]} ·{" "}
            {(item.picked_labels?.length ? item.picked_labels : item.picked_tickers.map(shortTicker)).slice(0, 3).join(", ")}
            {item.picked_tickers.length > 3 ? "…" : ""} · {formatDateTime(item.created_at)}
          </option>
        ))}
      </select>
    </label>
  );
}
