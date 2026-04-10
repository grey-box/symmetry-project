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

    return axiosInstance.post<TranslateArticleResponse>(
      '/symmetry/v1/wiki_translate/chunked_text',
      {
        source_language: sourceLanguage,
        target_language: targetLanguage,
        text: sourceText,
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
