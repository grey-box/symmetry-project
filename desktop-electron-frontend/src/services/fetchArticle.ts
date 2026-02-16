import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'
import { FetchArticleResponse } from '@/models/apis/FetchArticleResponse'

// API for getting Wikipedia articles
export async function fetchArticle(sourceArticleUrl: string): Promise<AxiosResponse<FetchArticleResponse>> {
  console.log('[DEBUG] fetchArticle called with URL:', sourceArticleUrl);
  
  try {
    const axiosInstance = await getAxiosInstance();
    
    return axiosInstance.get<FetchArticleResponse>('/symmetry/v1/wiki/articles', {
      params: { query: sourceArticleUrl },
      paramsSerializer: (params) => {
        const { query } = params;
        return `query=${encodeURIComponent(query)}`;
      }
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}

