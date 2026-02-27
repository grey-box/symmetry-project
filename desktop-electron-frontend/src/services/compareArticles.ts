import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'

// API call for semantic comparison of articles
// The backend now supports an optional similarity threshold override. If the
// client passes `null` or omits this value the server will compute a threshold
// automatically based on the language families of the two texts.  The field
// names below were also updated to match the new CompareRequest model.
export async function compareArticles(
  textA: string,
  textB: string,
  languageA: string,
  languageB: string,
  similarityThreshold?: number // optional override (0-1); undefined triggers auto-calc
): Promise<AxiosResponse<{
  comparisons: Array<{
    left_article_array: string[]
    right_article_array: string[]
    left_article_missing_info_index: number[]
    right_article_extra_info_index: number[]
  }>
}>> {
  try {
    const axiosInstance = await getAxiosInstance();

    console.log('[DEBUG] compareArticles called with textA length:', textA.length, 'textB length:', textB.length);
    console.log('[DEBUG] Languages - A:', languageA, 'B:', languageB);
    console.log('[DEBUG] Similarity Threshold:', similarityThreshold);

    return axiosInstance.post('/symmetry/v1/articles/compare', {
      original_article_content: textA,
      translated_article_content: textB,
      original_language: languageA,
      translated_language: languageB,
      comparison_threshold: similarityThreshold || null,
      model_name: 'sentence-transformers/LaBSE'
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}