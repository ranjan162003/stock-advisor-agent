import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { recommendationApi } from "../api/recommendationApi";
import { watchlistApi } from "../api/watchlistApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import {
  INITIAL_INVESTMENT_FORM_VALUES,
  InvestmentForm,
  type InvestmentFormValues,
} from "../components/investment-form/InvestmentForm";
import { DisclaimerBanner } from "../components/layout/DisclaimerBanner";
import { PageHeader } from "../components/layout/PageHeader";
import { ActiveModelSelector } from "../components/model-picker/ActiveModelSelector";
import { RecommendationProgress } from "../components/recommendation/RecommendationProgress";
import { RecommendationResults } from "../components/recommendation/RecommendationResults";
import { useProviderConnections } from "../context/ProviderConnectionsContext";
import type { ProviderId } from "../types/provider.types";
import type { RecommendationRequest, RecommendationResponse } from "../types/recommendation.types";
import { formatInr } from "../utils/displayFormatters";
import { RISK_LEVEL_LABELS, describeInvestmentMode } from "../utils/investmentLabels";

const UNIVERSE_LABELS = { default: "24 large NSE stocks", watchlist: "My watchlist", custom: "Custom list" };

export function AdvisorPage() {
  const { activeProviderId, activeModel, activeStatus } = useProviderConnections();
  const [formValues, setFormValues] = useState<InvestmentFormValues>(INITIAL_INVESTMENT_FORM_VALUES);
  const [watchlistSize, setWatchlistSize] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    watchlistApi
      .list()
      .then((items) => setWatchlistSize(items.length))
      .catch(() => setWatchlistSize(0));
  }, []);

  const validationError = validateForm(formValues, watchlistSize);
  const blocker =
    validationError ?? (activeStatus && !activeStatus.is_ready ? "Connect an AI model to continue." : null);
  const canSubmit = !isSubmitting && !blocker && Boolean(activeStatus?.is_ready);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    setError(null);
    setRecommendation(null);
    requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    try {
      setRecommendation(await recommendationApi.create(buildRequest(formValues, activeProviderId, activeModel)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const amount = Number(formValues.amountText);

  return (
    <div className="page">
      <PageHeader
        eyebrow="AI allocation agent"
        title="Advisor"
        description="Set your amount and risk level. The agent analyses a year of prices, fundamentals and news, then proposes a diversified split with its reasoning."
      />
      <DisclaimerBanner />

      <div className="advisor-layout">
        <InvestmentForm values={formValues} watchlistSize={watchlistSize} onChange={setFormValues} />

        <aside className="card advisor-run-panel">
          <h2 className="card__title">AI model</h2>
          <ActiveModelSelector />

          <dl className="run-summary">
            <div>
              <dt>Mode</dt>
              <dd>
                {describeInvestmentMode(
                  formValues.investmentMode,
                  formValues.investmentMode === "recurring" ? formValues.recurringFrequency : null,
                )}
              </dd>
            </div>
            <div>
              <dt>Amount</dt>
              <dd>{amount > 0 ? formatInr(amount) : "—"}</dd>
            </div>
            <div>
              <dt>Risk</dt>
              <dd>{RISK_LEVEL_LABELS[formValues.riskLevel]}</dd>
            </div>
            <div>
              <dt>Stocks</dt>
              <dd>{UNIVERSE_LABELS[formValues.universeSource]}</dd>
            </div>
          </dl>

          <button
            type="button"
            className="button button--primary button--large button--block"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            <Sparkles size={18} /> {isSubmitting ? "Analysing…" : "Get recommendation"}
          </button>
          {blocker && <p className="field__hint field__hint--warning">{blocker}</p>}
        </aside>
      </div>

      <div ref={resultsRef} className="advisor-results">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        {isSubmitting && <RecommendationProgress providerName={activeStatus?.display_name ?? "AI"} />}
        {recommendation && <RecommendationResults recommendation={recommendation} />}
      </div>
    </div>
  );
}

function parseCustomTickers(text: string): string[] {
  return text
    .split(/[\s,;]+/)
    .map((t) => t.trim())
    .filter(Boolean);
}

function validateForm(values: InvestmentFormValues, watchlistSize: number): string | null {
  const amount = Number(values.amountText);
  if (!values.amountText || !Number.isFinite(amount) || amount <= 0) return "Enter an amount greater than ₹0.";
  if (values.universeSource === "custom" && parseCustomTickers(values.customTickersText).length < 2)
    return "Enter at least 2 tickers.";
  if (values.universeSource === "watchlist" && watchlistSize < 2) return "Your watchlist needs at least 2 stocks.";
  return null;
}

function buildRequest(values: InvestmentFormValues, providerId: ProviderId, model: string): RecommendationRequest {
  return {
    investment_mode: values.investmentMode,
    amount: Number(values.amountText),
    recurring_frequency: values.investmentMode === "recurring" ? values.recurringFrequency : null,
    risk_level: values.riskLevel,
    provider_id: providerId,
    model_name: model || null,
    universe_source: values.universeSource,
    custom_tickers: values.universeSource === "custom" ? parseCustomTickers(values.customTickersText) : [],
  };
}
