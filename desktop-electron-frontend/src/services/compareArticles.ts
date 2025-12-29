import { AxiosResponse } from 'axios'
import { getAxiosInstance } from '@/services/axios'

// API call for semantic comparison of articles
export async function compareArticles(textA: string, textB: string): Promise<AxiosResponse<{
  missing_info: Array<{ missing_information: string }>;
  extra_info: Array<{ extra_information: string }>;
}>> {
  try {
    const axiosInstance = await getAxiosInstance();
    
    console.log('[DEBUG] compareArticles called with textA length:', textA.length, 'textB length:', textB.length);
    
    return axiosInstance.post('/symmetry/v1/articles/compare', {
      article_text_blob_1: textA,
      article_text_blob_2: textB,
      article_text_blob_1_language: 'en',
      article_text_blob_2_language: 'en',
      comparison_threshold: 0.5,
      model_name: 'default'
    });
  } catch (error) {
    console.error('Failed to get axios instance:', error);
    throw error;
  }
}