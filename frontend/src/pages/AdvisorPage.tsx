import { Check, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { recommendationApi } from "../api/recommendationApi";
import { mutualFundApi } from "../api/mutualFundApi";
import { watchlistApi } from "../api/watchlistApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { FormStep } from "../components/investment-form/FormStep";
import {
  INITIAL_INVESTMENT_FORM_VALUES,
  InvestmentForm,
  type InvestmentFormValues,
} from "../components/investment-form/InvestmentForm";
import type { WatchlistCounts } from "../components/investment-form/StockUniversePicker";
import { DisclaimerBanner } from "../components/layout/DisclaimerBanner";
import { PageHeader } from "../components/layout/PageHeader";
import { ActiveModelSelector } from "../components/model-picker/ActiveModelSelector";
import { RecommendationProgress } from "../components/recommendation/RecommendationProgress";
import { RecommendationResults } from "../components/recommendation/RecommendationResults";
import { useAssistantPageContext } from "../context/AssistantContext";
import { useProviderConnections } from "../context/ProviderConnectionsContext";
import type { ProviderId } from "../types/provider.types";
import type { RecommendationRequest, RecommendationResponse } from "../types/recommendation.types";
import { formatInr } from "../utils/displayFormatters";
import { ASSET_MIX_LABELS, RISK_LEVEL_LABELS, describeInvestmentMode } from "../utils/investmentLabels";

const UNIVERSE_LABELS = { default: "Built-in list", watchlist: "My watchlist", custom: "Custom stocks" };

export function AdvisorPage() {
  const { activeProviderId, activeModel, activeStatus } = useProviderConnections();
  const [formValues, setFormValues] = useState<InvestmentFormValues>(INITIAL_INVESTMENT_FORM_VALUES);
  const [watchlistCounts, setWatchlistCounts] = useState<WatchlistCounts>({ stocks: 0, funds: 0 });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  useAssistantPageContext("advisor", recommendation?.id);

  useEffect(() => {
    Promise.all([watchlistApi.list(), mutualFundApi.listWatchlist()])
      .then(([stocks, funds]) => setWatchlistCounts({ stocks: stocks.length, funds: funds.length }))
      .catch(() => setWatchlistCounts({ stocks: 0, funds: 0 }));
  }, []);

  const universeIssue = validateUniverse(formValues, watchlistCounts);
  const validationError = validateAmount(formValues) ?? universeIssue;
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
  const completedSteps = [!universeIssue, !validateAmount(formValues), true, Boolean(activeStatus?.is_ready)].filter(
    Boolean,
  ).length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="AI allocation agent"
        title="Advisor"
        description="Choose stocks, mutual funds or a mix, then set your amount and risk level. The agent analyses prices, fundamentals, fund track records and news, then proposes a diversified split with its reasoning."
      />
      <DisclaimerBanner />

      <div className="advisor-layout">
        <div className="form-steps">
          <InvestmentForm
            values={formValues}
            watchlistCounts={watchlistCounts}
            onChange={setFormValues}
            universeIssue={universeIssue}
          />
          <FormStep
            number={4}
            title="AI model"
            description="Which connected model writes the advice."
            complete={Boolean(activeStatus?.is_ready)}
            hasIssue={Boolean(activeStatus && !activeStatus.is_ready)}
            isLast
          >
            <ActiveModelSelector />
          </FormStep>
        </div>

        <aside className="card advisor-run-panel">
          <div className="card__title-row">
            <h2 className="card__title">Your plan</h2>
            <span className="run-progress">{completedSteps}/4 ready</span>
          </div>
          <div className="run-progress__track" aria-hidden="true">
            <span style={{ width: `${(completedSteps / 4) * 100}%` }} />
          </div>

          <dl className="run-summary">
            <div>
              <dt>Invest in</dt>
              <dd>{ASSET_MIX_LABELS[formValues.assetMix]}</dd>
            </div>
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
              <dt>Choose from</dt>
              <dd>{UNIVERSE_LABELS[formValues.universeSource]}</dd>
            </div>
            <div className="run-summary__wide">
              <dt>Model</dt>
              <dd>
                {activeStatus?.is_ready ? (
                  <>
                    <Check size={13} aria-hidden="true" /> {activeStatus.display_name} ·{" "}
                    {activeModel || activeStatus.default_model}
                  </>
                ) : (
                  "Not connected"
                )}
              </dd>
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
        {isSubmitting && (
          <RecommendationProgress
            providerId={activeProviderId}
            providerName={activeStatus?.display_name ?? "AI"}
            assetMix={formValues.assetMix}
          />
        )}
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

function validateAmount(values: InvestmentFormValues): string | null {
  const amount = Number(values.amountText);
  if (!values.amountText || !Number.isFinite(amount) || amount <= 0) return "Enter an amount greater than ₹0.";
  return null;
}

function validateUniverse(values: InvestmentFormValues, watchlist: WatchlistCounts): string | null {
  if (values.universeSource === "custom" && parseCustomTickers(values.customTickersText).length < 2)
    return "Enter at least 2 tickers.";
  if (values.universeSource === "watchlist") {
    if (values.assetMix === "stocks" && watchlist.stocks < 2) return "Your watchlist needs at least 2 stocks.";
    if (values.assetMix === "mutual_funds" && watchlist.funds < 2) return "Your watchlist needs at least 2 funds.";
    if (values.assetMix === "mixed" && (watchlist.stocks < 1 || watchlist.funds < 1))
      return "Your watchlist needs at least 1 stock and 1 fund.";
  }
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
    asset_mix: values.assetMix,
    universe_source: values.universeSource,
    custom_tickers:
      values.universeSource === "custom" && values.assetMix !== "mutual_funds"
        ? parseCustomTickers(values.customTickersText)
        : [],
  };
}
