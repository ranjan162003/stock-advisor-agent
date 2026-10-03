import type { ReactNode } from "react";

import { formatDateTime } from "../../utils/displayFormatters";

interface PrintableDocumentProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

/** Letterhead for exported PDFs: brand, title, date line, content, and the disclaimer footer. */
export function PrintableDocument({ title, subtitle, children }: PrintableDocumentProps) {
  return (
    <article className="printable">
      <header className="printable__header">
        <span className="printable__brand">
          <span className="sidebar__logo" aria-hidden="true">
            ₹
          </span>{" "}
          Stock Advisor
        </span>
        <h1>{title}</h1>
        <p className="printable__subtitle">{subtitle}</p>
      </header>
      {children}
      <footer className="printable__footer">
        AI-generated for personal research and education only — not financial advice. Data can be stale or incomplete,
        and past returns don't predict future ones. Exported {formatDateTime(new Date().toISOString())}.
      </footer>
    </article>
  );
}
