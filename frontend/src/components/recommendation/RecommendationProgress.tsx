import { useEffect, useState } from "react";

// The backend runs these stages in one request; we advance the checklist on a
// timer so a ~1 minute wait shows what's happening instead of a bare spinner.
const STAGES = [
  { label: "Fetching prices, fundamentals and news", startsAtSecond: 0 },
  { label: "Computing indicators and pre-scoring candidates", startsAtSecond: 8 },
  { label: "Agent is analysing candidates and choosing a split", startsAtSecond: 14 },
];

interface RecommendationProgressProps {
  providerName: string;
}

export function RecommendationProgress({ providerName }: RecommendationProgressProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const activeIndex = STAGES.reduce((active, stage, i) => (elapsedSeconds >= stage.startsAtSecond ? i : active), 0);

  return (
    <section className="card progress" aria-live="polite">
      <h2 className="card__title">Working on your recommendation…</h2>
      <ol className="progress__steps">
        {STAGES.map((stage, i) => (
          <li
            key={stage.label}
            className={`progress__step${i < activeIndex ? " progress__step--done" : ""}${
              i === activeIndex ? " progress__step--active" : ""
            }`}
          >
            <span className="progress__marker" aria-hidden="true">
              {i < activeIndex ? "✓" : i + 1}
            </span>
            {i === STAGES.length - 1 ? `${stage.label} (${providerName})` : stage.label}
          </li>
        ))}
      </ol>
      <p className="muted">
        {elapsedSeconds}s elapsed — this usually takes 30–90 seconds, longer with local models.
      </p>
    </section>
  );
}
