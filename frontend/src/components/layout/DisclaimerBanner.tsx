const DEFAULT_DISCLAIMER =
  "AI-generated opinion for personal research and education only — not licensed financial advice. " +
  "Data may be stale or incomplete and the model can be wrong. Any investment decision, and its risk, is yours.";

interface DisclaimerBannerProps {
  /** The backend sends its own wording with every recommendation; fall back to ours elsewhere. */
  text?: string;
}

export function DisclaimerBanner({ text = DEFAULT_DISCLAIMER }: DisclaimerBannerProps) {
  return (
    <aside className="disclaimer" role="note" aria-label="Disclaimer">
      <strong className="disclaimer__label">Not financial advice.</strong> {text}
    </aside>
  );
}
