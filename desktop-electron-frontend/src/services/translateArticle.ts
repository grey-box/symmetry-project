import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'
import { TranslateArticleResponse } from '@/models/apis/TranslateArticleResponse'

export async function translateArticle(
  sourceUrl: string,
  targetLanguage: string
): Promise<AxiosResponse<TranslateArticleResponse>> {
  try {
    const axiosInstance = await getAxiosInstance();

    return axiosInstance.get<TranslateArticleResponse>(
      '/symmetry/v1/wiki_translate/source_article',
      {
        params: {
          url: sourceUrl,
          language: targetLanguage,
        },
        timeout: 600000,
      }
    );
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}
