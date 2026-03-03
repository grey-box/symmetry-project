import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios';
import { FetchArticleResponse } from '@/models/apis/FetchArticleResponse';

function parseWikipediaUrl(url: string): { title: string; lang: string } | null {
  const urlPattern = /https?:\/\/([a-z-]{2,})\.wikipedia\.org\/wiki\/(.+)/;
  const match = url.match(urlPattern);
  
  if (match) {
    return {
      lang: match[1],
      title: decodeURIComponent(match[2].replace(/_/g, ' '))
    };
  }
  
  return null;
}

export async function fetchArticle(sourceArticleUrl: string): Promise<AxiosResponse<FetchArticleResponse>> {
  console.log('[DEBUG] fetchArticle called with URL:', sourceArticleUrl);
  
  try {
    const axiosInstance = await getAxiosInstance();
    
    const parsed = parseWikipediaUrl(sourceArticleUrl);
    if (parsed) {
      return axiosInstance.get<FetchArticleResponse>('/symmetry/v1/wiki/articles', {
        params: { query: parsed.title, lang: parsed.lang }
      });
    }
    
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

