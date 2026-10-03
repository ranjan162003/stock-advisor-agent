import { requestJson } from "./httpClient";

export interface UniverseStock {
  ticker: string;
  company_name: string;
  sector: string;
}

export const stockUniverseApi = {
  getDefaultUniverse: () => requestJson<UniverseStock[]>("/api/stocks/default-universe"),
};
