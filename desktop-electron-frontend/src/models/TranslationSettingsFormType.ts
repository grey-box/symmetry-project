import { TranslationTool } from '@/models/enums/TranslationTool'

export type TranslationSettingsFormType = {
  translationTool: TranslationTool;
  APIKey: string;
}
