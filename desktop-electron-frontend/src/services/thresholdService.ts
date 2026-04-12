import { getAxiosInstance } from '@/services/axios';

export interface ThresholdConfig {
  similarity_threshold: number;
  levenshtein_disambiguation_margin: number;
  family_thresholds: {
    same_family: number;
    ie_branches: number;
    unrelated: number;
    unknown: number;
  };
  band_thresholds: {
    same_family: { very_close: number; same_branch: number; same_family_distant: number; unrelated: number };
    ie_branches: { very_close: number; same_branch: number; same_family_distant: number; unrelated: number };
    different_families: { very_close: number; same_branch: number; same_family_distant: number; unrelated: number };
    unknown: { very_close: number; same_branch: number; same_family_distant: number; unrelated: number };
  };
}

const FALLBACK_THRESHOLDS: ThresholdConfig = {
  similarity_threshold: 0.65,
  levenshtein_disambiguation_margin: 0.08,
  family_thresholds: { same_family: 0.50, ie_branches: 0.60, unrelated: 0.70, unknown: 0.70 },
  band_thresholds: {
    same_family: { very_close: 0.75, same_branch: 0.55, same_family_distant: 0.30, unrelated: 0.15 },
    ie_branches: { very_close: 0.80, same_branch: 0.60, same_family_distant: 0.35, unrelated: 0.20 },
    different_families: { very_close: 0.85, same_branch: 0.65, same_family_distant: 0.40, unrelated: 0.25 },
    unknown: { very_close: 0.85, same_branch: 0.60, same_family_distant: 0.25, unrelated: 0.10 },
  },
};

let _cachedThresholds: ThresholdConfig | null = null;

export async function getThresholds(): Promise<ThresholdConfig> {
  if (_cachedThresholds) return _cachedThresholds;
  try {
    const axiosInstance = await getAxiosInstance();
    const response = await axiosInstance.get<ThresholdConfig>('/config/thresholds');
    _cachedThresholds = response.data;
    return _cachedThresholds;
  } catch (error) {
    console.warn('[thresholdService] Failed to fetch thresholds from backend, using defaults:', error);
    return FALLBACK_THRESHOLDS;
  }
}
