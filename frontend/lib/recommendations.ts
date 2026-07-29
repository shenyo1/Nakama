/**
 * Types for the AI-powered recommendation engine.
 */

export type ContentKind = "anime" | "comic" | "novel";

export interface RecommendationItem {
  title: string;
  slug?: string;
  source?: string;
  score: number;
  thumbnail?: string;
  genres?: string[];
}

export interface RecommendationRequest {
  title: string;
  kind: ContentKind;
  limit?: number;
  synopsis?: string;
  genres?: string[];
}

export interface RecommendationResponse {
  ok: boolean;
  anchor: string;
  kind: string;
  recommendations: RecommendationItem[];
  cached: boolean;
}
