import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'
import { TranslateArticleResponse } from '@/models/apis/TranslateArticleResponse'

// API call for getting translated article
export async function translateArticle(article_name: string, target_language: string): Promise<AxiosResponse<TranslateArticleResponse>> {
  try {
    const axiosInstance = await getAxiosInstance();
    
    console.log('[DEBUG] translateArticle called with article_name:', article_name, 'target_language:', target_language);
    
    return axiosInstance.get<TranslateArticleResponse>('/wiki_translate/source_article', {
      params: {
        article_name: article_name,
        target_language: target_language
      }
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}