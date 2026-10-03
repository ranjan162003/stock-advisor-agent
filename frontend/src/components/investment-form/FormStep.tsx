import { Check } from "lucide-react";
import type { ReactNode } from "react";

interface FormStepProps {
  number: number;
  title: string;
  description?: string;
  complete: boolean;
  /** A step with a problem shows a warning marker instead of a tick. */
  hasIssue?: boolean;
  isLast?: boolean;
  children: ReactNode;
}

/** One numbered step on the Advisor form, joined to the next by a rail; the number turns into a tick when done. */
export function FormStep({ number, title, description, complete, hasIssue, isLast, children }: FormStepProps) {
  const state = hasIssue ? "issue" : complete ? "done" : "todo";
  return (
    <section className={`form-step form-step--${state}${isLast ? " form-step--last" : ""}`} aria-label={`Step ${number}: ${title}`}>
      <div className="form-step__marker" aria-hidden="true">
        <span className="form-step__badge">{state === "done" ? <Check size={14} strokeWidth={3} /> : number}</span>
        {!isLast && <span className="form-step__rail" />}
      </div>
      <div className="card form-step__card">
        <div className="form-step__header">
          <h2 className="form-step__title">
            <span className="visually-hidden">Step {number}: </span>
            {title}
          </h2>
          {description && <p className="form-step__description">{description}</p>}
        </div>
        {children}
      </div>
    </section>
  );
}
