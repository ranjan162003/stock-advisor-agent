import type {
  ReturnPresetInfo,
  SipBacktestRequest,
  SipBacktestResponse,
  SipProjectionRequest,
  SipProjectionResponse,
} from "../types/planning.types";
import { requestJson } from "./httpClient";

export const planningApi = {
  getReturnPresets: () => requestJson<ReturnPresetInfo[]>("/api/planner/return-presets"),

  projectSip: (request: SipProjectionRequest) =>
    requestJson<SipProjectionResponse>("/api/planner/sip", { method: "POST", body: JSON.stringify(request) }),

  backtestSip: (request: SipBacktestRequest) =>
    requestJson<SipBacktestResponse>("/api/planner/sip-backtest", { method: "POST", body: JSON.stringify(request) }),
};
