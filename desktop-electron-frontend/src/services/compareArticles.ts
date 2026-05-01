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
  similarityThreshold: number = 0.65,
  modelName: string
): Promise<AxiosResponse<{
  comparisons: Array<{
    left_article_array: string[]
    right_article_array: string[]
    left_article_missing_info_index: number[]
    right_article_extra_info_index: number[]
  }>
  error_message?: string
}>> {
  try {
    const axiosInstance = await getAxiosInstance()

    console.log(
      '[DEBUG] compareArticles called with original length:',
      sourceArticleContent.length,
      'translated length:',
      targetArticleContent.length
    )
    console.log(
      '[DEBUG] Languages - original:',
      sourceLanguage,
      'translated:',
      targetLanguage
    )

    return axiosInstance.post('/symmetry/v1/articles/compare', {
      original_article_content: sourceArticleContent,
      translated_article_content: targetArticleContent,
      original_language: sourceLanguage,
      translated_language: targetLanguage,
      similarity_threshold: similarityThreshold,
      model_name: modelName,
    }, {
      timeout: 600000, // 10 minutes — large articles can take significant time
    })
  } catch (error) {
    console.error('Failed to get axios instance:', error)
    throw error
  }
}
