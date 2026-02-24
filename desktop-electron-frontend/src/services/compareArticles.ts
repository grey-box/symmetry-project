import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'

// API call for semantic comparison of articles
export async function compareArticles(
  textA: string,
  textB: string,
  languageA: string,
  languageB: string,
  similarityThreshold: number = 0.65
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

    return axiosInstance.post('/symmetry/v1/articles/compare', {
      original_article_content: originalArticleContent,
      translated_article_content: translatedArticleContent,
      original_language: originalLanguage,
      translated_language: translatedLanguage,
      similarity_threshold: similarityThreshold,
      model_name: 'sentence-transformers/LaBSE'
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error)
    throw error
  }
}
