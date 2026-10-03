import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import type { ChatCard, ChatFundDetails, ChatStockDetails } from "../../types/chat.types";
import {
  formatInr,
  formatInrCompact,
  formatInrPrecise,
  formatPercent,
  formatSignedPercent,
  parseCalendarDate,
} from "../../utils/displayFormatters";
import { RISK_LEVEL_LABELS } from "../../utils/investmentLabels";
import { SipBacktestChart } from "../planner/SipBacktestChart";
import { SipProjectionChart } from "../planner/SipProjectionChart";
import { AllocationStackedBar } from "../recommendation/AllocationStackedBar";

/** Cards the assistant attached to a reply. A search list is hidden once a more specific card exists. */
export function ChatCards({ cards }: { cards: ChatCard[] }) {
  const hasDetail = cards.some((c) => c.type !== "fund_list");
  const visible = hasDetail ? cards.filter((c) => c.type !== "fund_list") : cards;
  if (visible.length === 0) return null;
  return (
    <div className="chat-cards">
      {visible.map((card, i) => (
        <ChatCardView key={i} card={card} />
      ))}
    </div>
  );
}

function ChatCardView({ card }: { card: ChatCard }) {
  switch (card.type) {
    case "fund_list":
      return (
        <div className="chat-card">
          <div className="chat-card__eyebrow">Funds matching “{card.query}”</div>
          <ul className="chat-card__list">
            {card.funds.slice(0, 5).map((fund) => (
              <li key={fund.scheme_code}>
                <span className="chat-card__list-name">{fund.name}</span>
                <span className="muted">
                  {[fund.category, fund.nav ? `NAV ${formatInrPrecise(fund.nav)}` : null].filter(Boolean).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      );
    case "fund":
      return <FundCard fund={card.fund} />;
    case "fund_comparison":
      return <FundComparisonCard funds={card.funds} />;
    case "stock":
      return <StockCard stock={card.stock} />;
    case "sip_projection": {
      const r = card.result;
      return (
        <div className="chat-card">
          <div className="chat-card__eyebrow">
            {formatInr(r.monthly_amount)}/month for {r.years} years
            {r.annual_step_up_percent ? `, +${r.annual_step_up_percent}%/yr` : ""}
          </div>
          <div className="chat-card__metrics">
            <Metric label="Invested" value={formatInrCompact(r.total_invested)} />
            <Metric label="Bad case" value={formatInrCompact(r.bad_case)} />
            <Metric label="Typical" value={formatInrCompact(r.typical)} strong />
            <Metric label="Good case" value={formatInrCompact(r.good_case)} />
          </div>
          <SipProjectionChart points={r.yearly} goalAmount={r.goal_amount} />
          <p className="chat-card__footnote">{r.source_description}</p>
        </div>
      );
    }
    case "sip_backtest": {
      const r = card.result;
      return (
        <div className="chat-card">
          <div className="chat-card__eyebrow">
            {formatInr(r.monthly_amount)}/month since {formatMonth(r.start_date)} · real NAVs
          </div>
          <div className="chat-card__metrics">
            <Metric label="Invested" value={formatInrCompact(r.total_invested)} />
            <Metric label="Worth today" value={formatInrCompact(r.final_value)} strong />
            <Metric label="XIRR" value={formatPercent(r.xirr_percent)} tone={tone(r.xirr_percent)} />
            <Metric label={`FD at ${r.fixed_deposit_rate_percent}%`} value={formatInrCompact(r.fixed_deposit_value)} />
          </div>
          <SipBacktestChart points={r.timeline} />
          <p className="chat-card__footnote">
            {r.funds.map((f) => `${f.short_name} ${f.weight_percent}%`).join(" · ")} · worst dip{" "}
            {formatPercent(r.worst_drawdown_percent)}
          </p>
        </div>
      );
    }
    case "recommendation": {
      const rec = card.recommendation;
      return (
        <div className="chat-card">
          <div className="chat-card__header">
            <div className="chat-card__eyebrow">
              Recommendation #{rec.id} · {formatInr(rec.amount)} · {RISK_LEVEL_LABELS[rec.risk_level]}
            </div>
            <Link to={`/history/${rec.id}`} className="chat-card__link">
              Open <ExternalLink size={12} />
            </Link>
          </div>
          <AllocationStackedBar
            allocations={rec.allocations}
            amountLabel={rec.investment_mode === "recurring" ? "per period" : "now"}
          />
        </div>
      );
    }
    default:
      return null;
  }
}

function FundCard({ fund }: { fund: ChatFundDetails }) {
  return (
    <div className="chat-card">
      <div className="chat-card__header">
        <div>
          <div className="chat-card__title">{fund.name}</div>
          <div className="chat-card__eyebrow">
            {[fund.category, fund.fund_house, `risk ${fund.risk_class_1_to_5}/5`].filter(Boolean).join(" · ")}
          </div>
        </div>
        <div className="chat-card__price">
          {formatInrPrecise(fund.nav)}
          <span className="muted">NAV · {fund.nav_date}</span>
        </div>
      </div>
      <div className="chat-card__metrics">
        <Metric
          label="1 year"
          value={formatSignedPercent(fund.return_1y_percent)}
          tone={tone(fund.return_1y_percent)}
        />
        <Metric label="3y CAGR" value={formatPercent(fund.cagr_3y_percent)} tone={tone(fund.cagr_3y_percent)} />
        <Metric label="5y CAGR" value={formatPercent(fund.cagr_5y_percent)} tone={tone(fund.cagr_5y_percent)} />
        <Metric label="Worst fall (3y)" value={formatPercent(fund.worst_drawdown_3y_percent)} />
      </div>
    </div>
  );
}

function FundComparisonCard({ funds }: { funds: ChatFundDetails[] }) {
  const rows: {
    label: string;
    value: (f: ChatFundDetails) => string;
    best?: (f: ChatFundDetails) => number | null;
  }[] = [
    {
      label: "1 year",
      value: (f) => formatSignedPercent(f.return_1y_percent),
      best: (f) => f.return_1y_percent,
    },
    {
      label: "3y CAGR",
      value: (f) => formatPercent(f.cagr_3y_percent),
      best: (f) => f.cagr_3y_percent,
    },
    {
      label: "5y CAGR",
      value: (f) => formatPercent(f.cagr_5y_percent),
      best: (f) => f.cagr_5y_percent,
    },
    {
      label: "Volatility",
      value: (f) => formatPercent(f.volatility_percent),
      best: (f) => (f.volatility_percent === null ? null : -f.volatility_percent),
    },
    {
      label: "Worst fall (3y)",
      value: (f) => formatPercent(f.worst_drawdown_3y_percent),
      best: (f) => f.worst_drawdown_3y_percent,
    },
    {
      label: "Sharpe (3y)",
      value: (f) => (f.sharpe_3y === null ? "—" : f.sharpe_3y.toFixed(2)),
      best: (f) => f.sharpe_3y,
    },
  ];
  return (
    <div className="chat-card">
      <div className="chat-card__eyebrow">Side by side · best in each row highlighted</div>
      <div className="table-scroll">
        <table className="chat-compare">
          <thead>
            <tr>
              <th />
              {funds.map((f) => (
                <th key={f.scheme_code}>{f.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const scores = funds.map((f) => row.best?.(f) ?? null);
              const top = Math.max(...scores.filter((s): s is number => s !== null));
              return (
                <tr key={row.label}>
                  <th scope="row">{row.label}</th>
                  {funds.map((f, i) => (
                    <td
                      key={f.scheme_code}
                      className={scores[i] === top && funds.length > 1 ? "chat-compare__best" : undefined}
                    >
                      {row.value(f)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StockCard({ stock }: { stock: ChatStockDetails }) {
  return (
    <div className="chat-card">
      <div className="chat-card__header">
        <div>
          <div className="chat-card__title">{stock.name}</div>
          <div className="chat-card__eyebrow">
            {[stock.ticker.replace(/\.(NS|BO)$/, ""), stock.sector].filter(Boolean).join(" · ")}
          </div>
        </div>
        <div className="chat-card__price">
          {formatInrPrecise(stock.price)}
          <span className="muted">last close</span>
        </div>
      </div>
      <div className="chat-card__metrics">
        <Metric
          label="1 month"
          value={formatSignedPercent(stock.return_1m_percent)}
          tone={tone(stock.return_1m_percent)}
        />
        <Metric
          label="1 year"
          value={formatSignedPercent(stock.return_1y_percent)}
          tone={tone(stock.return_1y_percent)}
        />
        <Metric label="P/E" value={stock.pe === null ? "—" : stock.pe.toFixed(1)} />
        <Metric label="ROE" value={formatPercent(stock.roe_percent)} />
      </div>
      {stock.headlines.length > 0 && (
        <ul className="chat-card__headlines">
          {stock.headlines.slice(0, 3).map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  strong,
}: {
  label: string;
  value: string;
  tone?: "good" | "critical";
  strong?: boolean;
}) {
  return (
    <div className={`chat-metric${tone ? ` chat-metric--${tone}` : ""}${strong ? " chat-metric--strong" : ""}`}>
      <span className="chat-metric__label">{label}</span>
      <span className="chat-metric__value">{value}</span>
    </div>
  );
}

function tone(value: number | null | undefined): "good" | "critical" | undefined {
  if (value === null || value === undefined || value === 0) return undefined;
  return value > 0 ? "good" : "critical";
}

function formatMonth(isoDate: string): string {
  return parseCalendarDate(isoDate).toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric",
  });
}
