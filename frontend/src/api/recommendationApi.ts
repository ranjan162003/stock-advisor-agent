import type {
  RecommendationHistoryItem,
  RecommendationRequest,
  RecommendationResponse,
} from "../types/recommendation.types";
import { requestJson } from "./httpClient";

export const recommendationApi = {
  create: (request: RecommendationRequest) =>
    requestJson<RecommendationResponse>("/api/recommendations", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  listHistory: (limit = 50) => requestJson<RecommendationHistoryItem[]>(`/api/recommendations?limit=${limit}`),

  getById: (id: number) => requestJson<RecommendationResponse>(`/api/recommendations/${id}`),

  remove: (id: number) => requestJson<void>(`/api/recommendations/${id}`, { method: "DELETE" }),
};
