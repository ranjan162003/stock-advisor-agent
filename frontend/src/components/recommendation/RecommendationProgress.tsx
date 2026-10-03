import { Check } from "lucide-react";
import { useEffect, useState } from "react";

import type { ProviderId } from "../../types/provider.types";
import type { AssetMix } from "../../types/recommendation.types";
import { ProviderLogo } from "../connectors/ProviderLogo";

// The backend runs the whole pipeline in one request, so stages advance on a
// timer: a ~1 minute wait shows what's happening instead of a bare spinner.
const STAGE_START_SECONDS = [0, 7, 14];
const MESSAGE_ROTATE_MS = 2800;
// Progress approaches (but never reaches) 95% — the real finish replaces this view.
const PROGRESS_TIME_CONSTANT_SECONDS = 40;

const CHART_PATH =
  "M0,70 C30,62 45,74 70,58 S115,40 140,48 S185,66 210,44 S255,20 280,30 S325,52 350,34 S395,12 420,18 S470,30 500,10";

interface RecommendationProgressProps {
  providerId: ProviderId;
  providerName: string;
  assetMix: AssetMix;
}

export function RecommendationProgress({ providerId, providerName, assetMix }: RecommendationProgressProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const stages = buildStages(assetMix, providerName);
  const messages = buildMessages(assetMix, providerName);
  const activeStage = STAGE_START_SECONDS.reduce((active, start, i) => (elapsedSeconds >= start ? i : active), 0);
  const messageIndex = Math.floor((elapsedSeconds * 1000) / MESSAGE_ROTATE_MS) % messages.length;
  const progressPercent = Math.round(95 * (1 - Math.exp(-elapsedSeconds / PROGRESS_TIME_CONSTANT_SECONDS)));

  return (
    <section className="card analysis-loader" aria-live="polite" aria-busy="true">
      <div className="analysis-loader__hero">
        <div className="ai-orb" aria-hidden="true">
          <span className="ai-orb__ring" />
          <span className="ai-orb__ring ai-orb__ring--delayed" />
          <span className="ai-orb__halo" />
          <span className="ai-orb__core">
            <ProviderLogo providerId={providerId} size={40} />
          </span>
        </div>

        <div className="analysis-loader__text">
          <span className="analysis-loader__eyebrow">
            <span className="live-dot" aria-hidden="true" /> Analysing · {formatElapsed(elapsedSeconds)}
          </span>
          <h2 className="analysis-loader__title">Building your portfolio</h2>
          <p key={messageIndex} className="analysis-loader__message">
            {messages[messageIndex]}
          </p>
          <div
            className="analysis-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
            aria-label="Estimated progress"
          >
            <div className="analysis-progress__fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </div>

      <div className="pulse-chart" aria-hidden="true">
        <svg viewBox="0 0 500 80" preserveAspectRatio="none">
          <defs>
            <linearGradient id="pulse-chart-line" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="55%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#c026d3" />
            </linearGradient>
            <linearGradient id="pulse-chart-area" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path className="pulse-chart__area" d={`${CHART_PATH} L500,80 L0,80 Z`} fill="url(#pulse-chart-area)" />
          <path
            className="pulse-chart__line"
            d={CHART_PATH}
            fill="none"
            stroke="url(#pulse-chart-line)"
            strokeWidth="2"
            strokeLinecap="round"
            pathLength={1}
          />
        </svg>
        <span className="pulse-chart__scanner" />
      </div>

      <ol className="analysis-steps">
        {stages.map((stage, i) => {
          const state = i < activeStage ? "done" : i === activeStage ? "active" : "pending";
          return (
            <li key={stage.title} className={`analysis-step analysis-step--${state}`}>
              <span className="analysis-step__marker" aria-hidden="true">
                {state === "done" ? <Check size={14} strokeWidth={3} /> : i + 1}
              </span>
              <div>
                <div className="analysis-step__title">{stage.title}</div>
                <div className="analysis-step__detail">{stage.detail}</div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="skeleton-preview" aria-hidden="true">
        <div className="skeleton skeleton--bar" />
        {[0, 1, 2].map((row) => (
          <div key={row} className="skeleton-row">
            <span className="skeleton skeleton--dot" />
            <span className="skeleton skeleton--text" />
            <span className="skeleton skeleton--num" />
          </div>
        ))}
      </div>

      <p className="analysis-loader__footnote">
        Usually 30–90 seconds with cloud models; local models on a CPU can take several minutes.
      </p>
    </section>
  );
}

function buildStages(assetMix: AssetMix, providerName: string) {
  const data =
    assetMix === "stocks"
      ? "Prices, fundamentals and news"
      : assetMix === "mutual_funds"
        ? "NAV history and fund categories"
        : "Stock prices, news and fund NAVs";
  const metrics =
    assetMix === "stocks"
      ? "Returns, RSI, volatility, pre-scores"
      : assetMix === "mutual_funds"
        ? "CAGR, drawdowns, Sharpe, pre-scores"
        : "Indicators, fund metrics, pre-scores";
  return [
    { title: "Gathering market data", detail: data },
    { title: "Crunching the numbers", detail: metrics },
    { title: `${providerName} is choosing your split`, detail: "Weighing candidates against your risk level" },
  ];
}

function buildMessages(assetMix: AssetMix, providerName: string): string[] {
  const stockMessages = [
    "Pulling a year of daily prices for NSE stocks…",
    "Reading the latest company headlines…",
    "Computing moving averages, RSI and volatility…",
    "Scoring momentum, quality and valuation…",
    "Shortlisting across sectors so nothing is over-concentrated…",
  ];
  const fundMessages = [
    "Loading full NAV history for each fund…",
    "Computing 3- and 5-year CAGR…",
    "Measuring worst drawdowns and Sharpe ratios…",
    "Matching fund categories to your risk level…",
  ];
  const agentMessages = [
    `${providerName} is comparing the shortlisted candidates…`,
    `${providerName} is balancing risk against return…`,
    "Checking the weights add up to exactly 100%…",
    "Turning weights into rupee amounts…",
  ];
  if (assetMix === "stocks") return [...stockMessages, ...agentMessages];
  if (assetMix === "mutual_funds") return [...fundMessages, ...agentMessages];
  return [
    stockMessages[0],
    fundMessages[0],
    stockMessages[2],
    fundMessages[2],
    `${providerName} is deciding the stock vs fund balance…`,
    ...agentMessages,
  ];
}

function formatElapsed(seconds: number): string {
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}
