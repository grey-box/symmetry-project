import { TranslationFormType } from '@/models/TranslationFormType'
import { TranslationSettingsFormType } from '@/models/TranslationSettingsFormType'

export type FetchArticleRequest = Pick<TranslationFormType, 'sourceArticleUrl'> &
  Pick<TranslationSettingsFormType, 'translationTool'> & {
  targetLanguage?: string
  deepLApiKey?: string
};