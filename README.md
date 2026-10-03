# Stock Advisor Agent

> **Not financial advice.** This app produces AI-generated opinions for personal research and
> education only. Data can be stale or incomplete and the model can be wrong. Any money you invest
> based on its output is your own decision and risk.

Enter an amount (one-time or recurring) and a risk preference, then pick an AI model (**Claude**,
**Gemini** or a local **Ollama** model). The agent pulls a year of price history, fundamentals and
recent news for a set of Indian stocks, scores them, and asks the model to propose a diversified
split, with its reasoning, the risks, and the whole-share count each amount buys.

![flow](https://img.shields.io/badge/React-Vite-blue) ![api](https://img.shields.io/badge/Python-FastAPI-green)

## How it works

```
React UI ──► FastAPI ──► resolve tickers (default 24 NSE large caps / watchlist / custom)
                     ──► market data (yfinance: prices, fundamentals, news) ─► SQLite cache
                     ──► indicators (SMA, RSI, returns, volatility, drawdown) + fundamentals
                     ──► rule-based pre-score ─► shortlist (sector-capped)
                     ──► LLM provider (Claude / Gemini / Ollama) ─► JSON picks + weights
                     ──► rupee split + whole shares ─► saved to history
```

| Mode | Output |
|---|---|
| **One-time** | Rupee amount and approximate whole shares per stock, to invest now |
| **Recurring** (monthly/yearly) | Target **% allocation** to re-apply to each contribution (plus this period's rupee split) |

### Connecting a model

| Provider | Primary | Fallback |
|---|---|---|
| Claude | **Log in with Claude**: opens `claude auth login` (Claude Code CLI) and uses your Claude.ai plan | Paste an Anthropic API key |
| Gemini | **Log in with Google**: opens the `gemini` CLI's Google login (free-tier quota) | Paste a Google AI Studio API key |
| Ollama | Runs locally, no login; just have `ollama serve` running with a model pulled | — |

API keys go into your **OS credential vault** (Windows Credential Manager / macOS Keychain via
`keyring`). They're never written to a file and are never returned by the API.

## Project structure

```
stock-advisor-agent/
├── backend/                              Python · FastAPI
│   ├── app/
│   │   ├── main.py                       App factory, CORS, lifespan (DB init)
│   │   ├── core/
│   │   │   ├── app_settings.py           Typed settings (env: STOCK_ADVISOR_*)
│   │   │   ├── app_exceptions.py         Domain errors → HTTP status mapping
│   │   │   └── logging_config.py
│   │   ├── db/
│   │   │   ├── database_session.py       Engine, session factory, FastAPI dependency
│   │   │   ├── orm_models.py             Watchlist, market-data cache, recommendation history
│   │   │   └── repositories/             One file per table: queries only
│   │   ├── schemas/                      Pydantic request/response contracts
│   │   ├── data_sources/
│   │   │   ├── default_stock_universe.py 24 NSE large caps + ticker normalizing
│   │   │   ├── yfinance_market_data_client.py
│   │   │   └── news_headlines_client.py  Yahoo search news (+ optional Finnhub)
│   │   ├── analysis/
│   │   │   ├── technical_indicators.py   SMA, RSI, returns, volatility, drawdown
│   │   │   ├── fundamentals_extractor.py
│   │   │   ├── candidate_scoring.py      Transparent pre-score + sector-capped shortlist
│   │   │   └── stock_snapshot_builder.py Cache-aware per-stock data assembly
│   │   ├── agent/
│   │   │   ├── recommendation_agent.py   Prompt → LLM → parse (with one self-repair retry)
│   │   │   ├── recommendation_prompt_builder.py
│   │   │   ├── recommendation_response_parser.py
│   │   │   ├── allocation_calculator.py  % → ₹ amounts + whole shares
│   │   │   └── providers/
│   │   │       ├── base_llm_provider.py  The one interface every provider implements
│   │   │       ├── claude_provider.py    Claude Code CLI login or Anthropic API key
│   │   │       ├── gemini_provider.py    Gemini CLI Google login or API key
│   │   │       ├── ollama_provider.py    Local Ollama server
│   │   │       ├── cli_process_runner.py Run vendor CLIs / open login terminals
│   │   │       └── llm_provider_registry.py
│   │   ├── security/api_key_vault.py     OS-keyring storage for API keys
│   │   ├── services/                     Use-case orchestration (pipeline, history, watchlist)
│   │   └── api/
│   │       ├── api_router.py             Mounts every route module under /api
│   │       └── routes/                   health · providers · recommendations · watchlist · stocks
│   ├── tests/                            pytest (unit + end-to-end API with fakes)
│   ├── pyproject.toml · uv.lock          Dependencies (managed with uv) + exact locked versions
│   ├── .python-version                   Python 3.10
│   └── .env.example
│
└── frontend/                             React 18 · TypeScript · Vite
    └── src/
        ├── main.tsx · App.tsx            Entry + routes (/, /history/:id, /watchlist, /connectors)
        ├── api/                          httpClient + one client per backend resource
        ├── types/                        *.types.ts mirroring backend schemas
        ├── context/ProviderConnectionsContext.tsx  App-wide connector status + active model
        ├── hooks/useProviderStatuses.ts  Provider status + login polling
        ├── pages/                        AdvisorPage · HistoryPage · WatchlistPage · AgentConnectorsPage
        ├── components/
        │   ├── layout/                   AppShell · AppSidebar · PageHeader · DisclaimerBanner
        │   ├── common/                   ErrorAlert · LoadingSpinner · CopyableCommand
        │   ├── connectors/               ConnectorCard · ProviderLogo · ConnectorStatusBadge · ApiKeyForm
        │   ├── investment-form/          InvestmentForm · InvestmentModeToggle · RiskLevelSlider · StockUniversePicker
        │   ├── model-picker/             ActiveModelSelector (compact chooser on the Advisor page)
        │   ├── recommendation/           RecommendationResults · AllocationStackedBar · AllocationTable ·
        │   │                             AgentReasoningPanel · CandidatesConsideredTable · RecommendationProgress
        │   ├── history/                  RecommendationHistoryList
        │   └── watchlist/                WatchlistManager
        ├── utils/                        displayFormatters (₹, %) · investmentLabels
        └── styles/global.css             Design tokens, light/dark themes
```

## Getting started

### 1. Install the prerequisites (once per computer)

| Tool | Why | Install | Check |
|---|---|---|---|
| **Node.js 20+** | Runs the React frontend and the dev scripts | https://nodejs.org (LTS) | `node --version` |
| **uv** | Installs Python 3.10 and the backend packages | Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |

You don't need to install Python yourself. uv downloads the right version if it's missing.

You need **at least one AI model** to get recommendations. Pick one or more:

| Model | Install | How it connects |
|---|---|---|
| **Claude** (recommended) | [Claude Code](https://claude.com/claude-code): `npm install -g @anthropic-ai/claude-code` | Browser login with your Claude.ai account, or an API key |
| **Gemini** | `npm install -g @google/gemini-cli` | Browser login with your Google account, or an API key |
| **Ollama** (free, offline) | https://ollama.com, then `ollama pull llama3.1` | Runs locally, no login. Slow without a GPU (several minutes per recommendation) |

### 2. Install the project (once, and again after pulling new changes)

```bash
cd scripts
npm run setup
```

This checks your tools, then installs everything:

1. **Backend:** `uv sync` installs Python and the exact packages from `backend/uv.lock`
2. **Frontend:** `npm install` in `frontend/`
3. **Dev runner:** `npm install` in `scripts/`

> **Project inside OneDrive?** OneDrive locks the package files of a Python environment, which
> makes installs fail with "Access is denied". The scripts detect this and keep the backend's
> environment in `%LOCALAPPDATA%\stock-advisor-agent\backend-venv` instead of `backend/.venv`.
> Your code stays where it is.

### 3. Run the app

**Windows:** double-click **`scripts\start-dev.cmd`** (it runs setup automatically the first time).

**Any OS:**

```bash
cd scripts
npm run dev
```

This starts both servers in one terminal:

| Server | URL | Log prefix |
|---|---|---|
| Backend (FastAPI) | http://localhost:8000 — API docs at http://localhost:8000/docs | `[api]` (magenta) |
| Frontend (React) | **http://localhost:5173**, the app itself | `[web]` (cyan) |

Open **http://localhost:5173**. Press **Ctrl+C** once to stop both.

### 4. Connect a model and get a recommendation

1. In the app, open **Agent connectors** in the sidebar.
2. On a model's card, click **Connect with browser** (Claude/Gemini) and finish signing in. The card
   turns *Connected* by itself. Or click **Add key** to paste an API key, or start Ollama.
3. Click **Use for advice** on the model you want.
4. Go to **Advisor**, enter an amount and risk level, and click **Get recommendation**
   (about 30–90 s with Claude).

### Everyday commands

All of these run from the `scripts/` folder:

| Command | What it does |
|---|---|
| `npm run setup` | Install or update everything (after `git pull`, or if something is missing) |
| `npm run dev` | Start backend + frontend together |
| `npm test` | Backend tests (pytest) + frontend type-check and build |
| `npm run dev:api` | Start only the backend |
| `npm run dev:web` | Start only the frontend |

```
scripts/
├── setup.mjs                 npm run setup: checks tools, installs backend + frontend + runner
├── run-backend.mjs           Starts uvicorn (or pytest with --tests) via `uv run`
├── backend-environment.mjs   Picks where the Python environment lives (moves it out of OneDrive)
├── start-dev.cmd             Windows double-click launcher
└── package.json              The npm commands above
```

### Running the servers by hand (optional)

```bash
# Backend: terminal 1
cd backend
uv sync
uv run uvicorn app.main:app --reload --reload-dir app --port 8000

# Frontend: terminal 2
cd frontend
npm install
npm run dev
```

`--reload-dir app` makes the backend restart only when your code changes. Without it, uvicorn also
watches the virtualenv and restarts endlessly while OneDrive syncs it. If the project is inside
OneDrive, set `$env:UV_PROJECT_ENVIRONMENT="$env:LOCALAPPDATA\stock-advisor-agent\backend-venv"`
first, so the manual commands use the same environment as the scripts.

### Managing Python packages (uv)

```bash
cd backend
uv add <package>          # add a dependency (updates pyproject.toml + uv.lock)
uv add --dev <package>    # add a dev-only tool
uv remove <package>
uv lock --upgrade         # bump everything to the newest allowed versions
```

Commit `pyproject.toml` and `uv.lock` together. The virtualenv is never committed.

### Troubleshooting

| Problem | Fix |
|---|---|
| `port already in use` / `WinError 10013` | Something from an earlier run is still running. Close old terminals, or run `Get-Process python, node \| Stop-Process` (PowerShell), then start again. |
| `Access is denied` during `uv sync` | The backend is still running and locking its packages. Stop it (Ctrl+C), then `npm run setup` again. |
| `EPERM ... node_modules\.vite` | OneDrive locked Vite's cache. Already handled: the cache lives in your temp folder (`vite.config.ts`). |
| Claude shows *Not connected* | Run `claude auth status` in a terminal. If logged out, click **Connect with browser** on the Claude card. |
| Ollama is very slow / times out | It's running on your CPU. Try a smaller model (`ollama pull llama3.2:3b`) or use Claude. |
| "The model's reply wasn't valid JSON" | Try again or use a stronger model. The error shows what the model actually replied. |

## Configuration

Copy `backend/.env.example` to `backend/.env` to override defaults: Ollama URL/model, default
Claude/Gemini model, cache TTL, how many candidates go to the LLM, an optional Finnhub key for
extra news, and more.

## Notes and limits

- Market data comes from Yahoo Finance via `yfinance` (free, unofficial). It's cached for 6 hours.
- Plain tickers default to NSE (`INFY` → `INFY.NS`). Use `.BO` for BSE or a full Yahoo symbol for
  other exchanges.
- The app **never places trades**. Recurring mode gives target percentages; you invest yourself.
- With the Claude CLI login, the model is passed as a family alias (`opus`/`sonnet`/`haiku`) so
  older Claude Code builds still work. With an API key, the exact model id is used.
