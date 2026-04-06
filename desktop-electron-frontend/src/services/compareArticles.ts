import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'

/**
 * Compare two article texts using semantic similarity (legacy plain-text comparison).
 * Calls POST /symmetry/v1/articles/compare with LaBSE embeddings.
 */
export async function compareArticles(
  sourceArticleContent: string,
  targetArticleContent: string,
  sourceLanguage: string,
  targetLanguage: string,
  similarityThreshold: number = 0.65
): Promise<AxiosResponse<{
  comparisons: Array<{
    left_article_array: string[]
    right_article_array: string[]
    left_article_missing_info_index: number[]
    right_article_extra_info_index: number[]
  }>
}>> {
  const axiosInstance = await getAxiosInstance()

    console.log('[DEBUG] compareArticles called with original length:', originalArticleContent.length, 'translated length:', translatedArticleContent.length);
    console.log('[DEBUG] Languages - original:', originalLanguage, 'translated:', translatedLanguage);

    return axiosInstance.post('/symmetry/v1/articles/compare', {
      original_article_content: originalArticleContent,
      translated_article_content: translatedArticleContent,
      original_language: originalLanguage,
      translated_language: translatedLanguage,
      similarity_threshold: similarityThreshold,
      model_name: 'sentence-transformers/LaBSE'
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}
