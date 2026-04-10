import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'
import { TranslateArticleResponse } from '@/models/apis/TranslateArticleResponse'

export async function translateArticle(
  sourceText: string,
  sourceLanguage: string,
  targetLanguage: string,
  signal?: AbortSignal
): Promise<AxiosResponse<TranslateArticleResponse>> {
  try {
    const axiosInstance = await getAxiosInstance();
    
    console.log('[DEBUG] translateArticle called with article_name:', article_name, 'target_language:', target_language);
    
    return axiosInstance.get<TranslateArticleResponse>('/symmetry/v1/wiki_translate/source_article', {
      params: {
        title: article_name,
        language: target_language
      },
      {
        timeout: 600000,
        signal,
      }
    );
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}
