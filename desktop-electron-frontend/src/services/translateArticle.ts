import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'
import { TranslateArticleResponse } from '@/models/apis/TranslateArticleResponse'

export async function translateArticle(article_name: string, target_language: string): Promise<AxiosResponse<TranslateArticleResponse>> {
  try {
    const axiosInstance = await getAxiosInstance();
    
    console.log('[DEBUG] translateArticle called with article_name:', article_name, 'target_language:', target_language);
    
    return axiosInstance.get<TranslateArticleResponse>('/symmetry/v1/wiki_translate/source_article', {
      params: {
        title: article_name,
        language: target_language
      },
      paramsSerializer: (params) => {
        const paramsArray: string[] = []
        Object.entries(params).forEach(([key, value]) => {
          if (key === 'title') {
            paramsArray.push(`${key}=${value}`)
          } else {
            paramsArray.push(`${key}=${encodeURIComponent(value)}`)
          }
        })
        return paramsArray.join('&')
      }
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}