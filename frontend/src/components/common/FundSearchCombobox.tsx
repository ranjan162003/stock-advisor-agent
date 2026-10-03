import { ChevronDown, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type UIEvent } from "react";

import { mutualFundApi } from "../../api/mutualFundApi";
import type { FundCategory, FundSearchResult, UniverseFund } from "../../types/mutualFund.types";
import { formatInrPrecise } from "../../utils/displayFormatters";

const SEARCH_DEBOUNCE_MS = 120;
const SEARCH_LIMIT = 50;
const ALL_FUNDS_LIMIT = 5000;
const RENDER_PAGE = 120; // rows added each time you scroll near the bottom

export interface PickedFundOption {
  schemeCode: number;
  schemeName: string;
  shortName: string;
}

interface FundSearchComboboxProps {
  onSelect: (fund: PickedFundOption) => void;
  /** Funds already chosen — shown as "Added" and not selectable again. */
  selectedCodes?: Set<number>;
  placeholder?: string;
}

// The full list (~1,700 funds) is fetched once per page load and shared by every picker.
let allFundsCache: Promise<FundSearchResult[]> | null = null;
function loadAllFunds(): Promise<FundSearchResult[]> {
  allFundsCache ??= mutualFundApi.search("", { limit: ALL_FUNDS_LIMIT }).catch((err) => {
    allFundsCache = null;
    throw err;
  });
  return allFundsCache;
}

/**
 * One searchable dropdown of every active Indian mutual fund.
 * Open it to scroll the whole list (popular funds first), or type any part of a
 * name to filter — words in any order, abbreviations like "pru" work.
 * Category is an optional filter inside the dropdown. Keyboard: ↑/↓, Enter, Esc.
 */
export function FundSearchCombobox({ onSelect, selectedCodes = new Set(), placeholder }: FundSearchComboboxProps) {
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [includeAllPlans, setIncludeAllPlans] = useState(false);
  const [categories, setCategories] = useState<FundCategory[]>([]);
  const [popular, setPopular] = useState<UniverseFund[]>([]);
  const [allFunds, setAllFunds] = useState<FundSearchResult[]>([]);
  const [searchResults, setSearchResults] = useState<FundSearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [visibleCount, setVisibleCount] = useState(RENDER_PAGE);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    mutualFundApi.getCategories().then(setCategories).catch(() => setCategories([]));
    mutualFundApi.getDefaultUniverse().then(setPopular).catch(() => setPopular([]));
  }, []);

  // Load the full list the first time the dropdown opens.
  useEffect(() => {
    if (!isOpen || allFunds.length) return;
    setIsLoading(true);
    loadAllFunds()
      .then((funds) => {
        setAllFunds(funds);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setIsLoading(false));
  }, [isOpen, allFunds.length]);

  // Close when clicking anywhere outside the combobox.
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  // Typed text, a category, or "all plans" go to the server's forgiving search.
  const needsServerSearch = Boolean(query.trim() || category || includeAllPlans);
  useEffect(() => {
    if (!needsServerSearch) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      try {
        const found = await mutualFundApi.search(query.trim(), {
          category,
          includeAllPlans,
          limit: query.trim() ? SEARCH_LIMIT : ALL_FUNDS_LIMIT,
        });
        if (!cancelled) {
          setSearchResults(found);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, category, includeAllPlans, needsServerSearch]);

  const listed = needsServerSearch ? searchResults : allFunds;
  const popularCodes = useMemo(() => new Set(popular.map((p) => p.scheme_code)), [popular]);
  const groupedCategories = useMemo(() => groupBy(categories, (c) => c.group), [categories]);
  const visible = listed.slice(0, visibleCount);

  // Reset scroll position and highlight whenever the list changes.
  useEffect(() => {
    setActiveIndex(0);
    setVisibleCount(RENDER_PAGE);
    listRef.current?.scrollTo({ top: 0 });
  }, [listed]);

  const choose = (fund: FundSearchResult) => {
    if (selectedCodes.has(fund.scheme_code)) return;
    onSelect({ schemeCode: fund.scheme_code, schemeName: fund.scheme_name, shortName: shortFundName(fund.scheme_name) });
    setQuery("");
    setIsOpen(false);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((i) => {
        const next = Math.min(listed.length - 1, i + 1);
        if (next >= visibleCount - 5) setVisibleCount((c) => c + RENDER_PAGE);
        return next;
      });
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (event.key === "Enter" && isOpen && listed[activeIndex]) {
      event.preventDefault();
      choose(listed[activeIndex]);
    } else if (event.key === "Escape") {
      setIsOpen(false);
    }
  };

  // Keep the keyboard-highlighted row in view.
  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${activeIndex}"]`)?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const handleScroll = (event: UIEvent<HTMLUListElement>) => {
    const el = event.currentTarget;
    if (el.scrollTop + el.clientHeight > el.scrollHeight - 200 && visibleCount < listed.length) {
      setVisibleCount((c) => c + RENDER_PAGE);
    }
  };

  const showSections = !query.trim();
  const countLabel = isLoading && !listed.length
    ? "Loading funds…"
    : query.trim()
      ? `${listed.length}${listed.length === SEARCH_LIMIT ? "+" : ""} match${listed.length === 1 ? "" : "es"}`
      : `${listed.length.toLocaleString("en-IN")} funds — type to filter`;

  return (
    <div className="fund-combobox" ref={rootRef}>
      <div className="search-input fund-combobox__search">
        <Search size={16} aria-hidden="true" />
        <input
          className="input fund-combobox__input"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-label="Search mutual funds"
          placeholder={placeholder ?? "Select or search a fund — e.g. parag flexi, hdfc mid, sbi small"}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onClick={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="fund-combobox__toggle-button"
          aria-label={isOpen ? "Close fund list" : "Open fund list"}
          onClick={() => setIsOpen((open) => !open)}
        >
          <ChevronDown size={16} />
        </button>
      </div>

      {isOpen && (
        <div className="fund-combobox__panel">
          <div className="fund-combobox__panel-header">
            <span>{countLabel}</span>
            <div className="fund-combobox__filters">
              <select
                className="fund-combobox__category"
                value={category}
                aria-label="Filter by category (optional)"
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All categories</option>
                {[...groupedCategories.entries()].map(([group, items]) => (
                  <optgroup key={group} label={group}>
                    {items.map((c) => (
                      <option key={c.category} value={c.category}>
                        {c.label} ({c.fund_count})
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <label className="fund-combobox__toggle">
                <input type="checkbox" checked={includeAllPlans} onChange={(e) => setIncludeAllPlans(e.target.checked)} />
                Regular / IDCW too
              </label>
            </div>
          </div>
          {error && <p className="field__hint field__hint--warning">{error}</p>}
          {!isLoading && listed.length === 0 && !error && (
            <p className="fund-combobox__empty">No funds match. Try fewer words or just the fund house (e.g. “axis”).</p>
          )}
          <ul className="fund-combobox__list" id={listId} role="listbox" ref={listRef} onScroll={handleScroll}>
            {visible.map((fund, index) => {
              const isAdded = selectedCodes.has(fund.scheme_code);
              const isPopular = popularCodes.has(fund.scheme_code);
              const previousWasPopular = index > 0 && popularCodes.has(visible[index - 1].scheme_code);
              return (
                <FragmentWithHeading
                  key={fund.scheme_code}
                  heading={
                    showSections && index === 0 && isPopular
                      ? "Popular"
                      : showSections && !isPopular && (index === 0 || previousWasPopular)
                        ? category ? "A–Z" : "All funds A–Z"
                        : null
                  }
                >
                  <li
                    role="option"
                    data-index={index}
                    aria-selected={index === activeIndex}
                    aria-disabled={isAdded}
                    className={`fund-option${index === activeIndex ? " fund-option--active" : ""}${isAdded ? " fund-option--added" : ""}`}
                    onPointerEnter={() => setActiveIndex(index)}
                    onPointerDown={(e) => e.preventDefault()}
                    onClick={() => choose(fund)}
                  >
                    <span className="fund-option__name">
                      <Highlight text={fund.scheme_name} query={query} />
                    </span>
                    <span className="fund-option__meta">
                      {fund.category_label}
                      {fund.fund_house ? ` · ${fund.fund_house.replace(/ Mutual Fund$/i, "")}` : ""}
                      {fund.nav ? ` · NAV ${formatInrPrecise(fund.nav)}` : ""}
                      {!fund.is_direct_growth && <span className="tag">Regular / IDCW</span>}
                    </span>
                    {isAdded && <span className="fund-option__added">Added</span>}
                  </li>
                </FragmentWithHeading>
              );
            })}
            {visible.length < listed.length && <li className="fund-combobox__more">Scroll for more…</li>}
          </ul>
        </div>
      )}
    </div>
  );
}

function FragmentWithHeading({ heading, children }: { heading: string | null; children: React.ReactNode }) {
  return (
    <>
      {heading && (
        <li className="fund-combobox__section" role="presentation">
          {heading}
        </li>
      )}
      {children}
    </>
  );
}

/** Bold the parts of the name that match what was typed. */
function Highlight({ text, query }: { text: string; query: string }) {
  const words = query.toLowerCase().split(/\s+/).filter((w) => w.length >= 2);
  if (words.length === 0) return <>{text}</>;
  const pattern = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return (
    <>
      {text.split(pattern).map((part, i) =>
        words.includes(part.toLowerCase()) ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>,
      )}
    </>
  );
}

export function shortFundName(schemeName: string): string {
  const short = schemeName.split(/\s+-\s+|\(/)[0].replace(/\s+Fund$/i, "").trim() || schemeName;
  // Some AMFI names are ALL CAPS ("SBI SMALL CAP FUND"); show them in title case, keeping short acronyms.
  if (short !== short.toUpperCase()) return short;
  return short
    .toLowerCase()
    .split(" ")
    .map((word) => (word.length <= 3 && !/^(cap|and|the|of)$/.test(word) ? word.toUpperCase() : word[0].toUpperCase() + word.slice(1)))
    .join(" ");
}

function groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) groups.set(key(item), [...(groups.get(key(item)) ?? []), item]);
  return groups;
}
