import { NavLink } from "react-router-dom";

import type { RecommendationHistoryItem } from "../../types/recommendation.types";
import { formatDateTime, formatInr, shortTicker } from "../../utils/displayFormatters";
import { PROVIDER_LABELS, describeInvestmentMode } from "../../utils/investmentLabels";

interface RecommendationHistoryListProps {
  items: RecommendationHistoryItem[];
  onDelete: (id: number) => void;
}

export function RecommendationHistoryList({ items, onDelete }: RecommendationHistoryListProps) {
  return (
    <ul className="history-list">
      {items.map((item) => (
        <li key={item.id} className="history-list__item">
          <NavLink
            to={`/history/${item.id}`}
            className={({ isActive }) => `history-list__link${isActive ? " history-list__link--active" : ""}`}
          >
            <span className="history-list__amount">
              {formatInr(item.amount)}{" "}
              <span className="muted">· {describeInvestmentMode(item.investment_mode, item.recurring_frequency)}</span>
            </span>
            <span className="history-list__tickers">{(item.picked_labels?.length ? item.picked_labels : item.picked_tickers.map(shortTicker)).join(", ")}</span>
            <span className="history-list__meta">
              {formatDateTime(item.created_at)} · {PROVIDER_LABELS[item.provider_id]}
            </span>
          </NavLink>
          <button
            type="button"
            className="icon-button"
            aria-label={`Delete recommendation from ${formatDateTime(item.created_at)}`}
            onClick={() => onDelete(item.id)}
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  );
}
