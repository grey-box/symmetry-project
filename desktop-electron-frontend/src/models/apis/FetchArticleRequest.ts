import { TranslationFormType } from '@/models/TranslationFormType'
import { TranslationSettingsFormType } from '@/models/TranslationSettingsFormType'

/*
// Defines request structure which includes input type (Older logic)
export type FetchArticleRequest = Pick<TranslationFormType, 'sourceArticleUrl'> &
  Pick<TranslationSettingsFormType, 'translationTool'> & {
  targetLanguage?: string
  deepLApiKey?: string
};
*/

// Defines request structure which includes input type (new working logic)

export type FetchArticleRequest = {
  sourceArticleUrl: string;
};
