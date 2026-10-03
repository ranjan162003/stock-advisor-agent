import { FileUp, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { planningApi } from "../../api/planningApi";
import type { ParsedHolding } from "../../types/planning.types";
import { ErrorAlert } from "../common/ErrorAlert";

export interface HoldingRow {
  key: number;
  symbol: string;
  quantityText: string;
  label?: string;
}

let nextKey = 1;
export function newHoldingRow(symbol = "", quantityText = "", label?: string): HoldingRow {
  return { key: nextKey++, symbol, quantityText, label };
}

interface HoldingsEditorProps {
  rows: HoldingRow[];
  onChange: (rows: HoldingRow[]) => void;
}

/** Editable list of what you own now, with paste-from-broker import. */
export function HoldingsEditor({ rows, onChange }: HoldingsEditorProps) {
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const [parsed, setParsed] = useState<ParsedHolding[] | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const update = (key: number, patch: Partial<HoldingRow>) =>
    onChange(rows.map((row) => (row.key === key ? { ...row, ...patch, label: patch.symbol !== undefined ? undefined : row.label } : row)));

  const runImport = async () => {
    setIsImporting(true);
    setImportError(null);
    try {
      setParsed((await planningApi.importHoldings(importText)).holdings);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsImporting(false);
    }
  };

  const addParsed = () => {
    const matched = (parsed ?? []).filter((h) => h.matched && h.symbol && h.quantity);
    const kept = rows.filter((row) => row.symbol.trim());
    onChange([...kept, ...matched.map((h) => newHoldingRow(h.symbol!, String(h.quantity), h.display_name ?? undefined))]);
    setParsed(null);
    setImportText("");
    setShowImport(false);
  };

  return (
    <div className="holdings-editor">
      <div className="holdings-editor__header">
        <span className="field__label">What you own now</span>
        <button type="button" className="button button--ghost button--small" onClick={() => setShowImport((s) => !s)}>
          <FileUp size={14} /> Import from broker
        </button>
      </div>

      {showImport && (
        <div className="import-panel">
          <textarea
            className="input input--textarea"
            rows={5}
            placeholder={"Paste your holdings export (Zerodha, Groww, Upstox, Coin…), e.g.\nInstrument,Qty.\nTCS,10\nParag Parikh Flexi Cap Fund - Direct Growth,150.5"}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
          />
          <div className="button-row">
            <button
              type="button"
              className="button button--secondary button--small"
              disabled={!importText.trim() || isImporting}
              onClick={runImport}
            >
              {isImporting ? "Reading…" : "Read holdings"}
            </button>
          </div>
          {importError && <ErrorAlert message={importError} />}
          {parsed && (
            <>
              <ul className="import-results">
                {parsed.map((h, i) => (
                  <li key={i} className={h.matched ? "" : "import-results__item--bad"}>
                    <span>{h.matched ? "✓" : "✕"}</span>
                    <span className="import-results__text">
                      <strong>{h.input_text}</strong>
                      {h.matched ? ` → ${h.display_name} (${h.symbol}) · ${h.quantity}` : ""}
                      {h.note && <span className="muted"> — {h.note}</span>}
                    </span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="button button--primary button--small"
                disabled={!parsed.some((h) => h.matched)}
                onClick={addParsed}
              >
                Add {parsed.filter((h) => h.matched).length} matched holding(s)
              </button>
            </>
          )}
        </div>
      )}

      <div className="holdings-rows">
        {rows.length === 0 && <p className="muted">Nothing yet — add rows, import from your broker, or just invest new cash.</p>}
        {rows.map((row) => (
          <div key={row.key} className="holding-row">
            <div className="holding-row__symbol">
              <input
                className="input"
                placeholder="TCS · INFY · MF:122639"
                value={row.symbol}
                onChange={(e) => update(row.key, { symbol: e.target.value })}
                aria-label="Ticker or fund code"
              />
              {row.label && <span className="holding-row__label">{row.label}</span>}
            </div>
            <input
              className="input holding-row__qty"
              type="number"
              min={0}
              step="any"
              placeholder="Qty / units"
              value={row.quantityText}
              onChange={(e) => update(row.key, { quantityText: e.target.value })}
              aria-label="Quantity"
            />
            <button
              type="button"
              className="icon-button"
              aria-label="Remove holding"
              onClick={() => onChange(rows.filter((r) => r.key !== row.key))}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
        <button type="button" className="button button--ghost button--small" onClick={() => onChange([...rows, newHoldingRow()])}>
          <Plus size={14} /> Add holding
        </button>
      </div>
      <p className="field__hint">
        Stocks: NSE ticker and number of shares. Funds: <code>MF:</code> + scheme code (find it via Watchlist → Mutual
        funds search) and your units.
      </p>
    </div>
  );
}
