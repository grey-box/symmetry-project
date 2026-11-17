/**
 * Settings for the AI agent used by the Through-Time AI summary.
 *
 * The provider, model and endpoint URL are kept in localStorage so they are
 * remembered between runs. The API key is only kept in sessionStorage, so it
 * is forgotten when the app window closes and has to be entered again on the
 * next run. It is never written to disk by the app.
 *
 * The key is sent to the local backend with each summary request, which
 * passes it to the chosen provider and never logs or stores it.
 */

export type AiProvider = 'anthropic' | 'openai' | 'gemini' | 'groq' | 'openrouter' | 'custom';

export interface AiAgentSettings {
  provider: AiProvider;
  model: string;
  apiKey: string;
  baseUrl: string;
}

export interface AiProviderInfo {
  id: AiProvider;
  label: string;
  defaultModel: string;
  keyHint: string;
  needsKey: boolean;
}

// Default models match the backend (app/services/ai_agent.py). The model
// box in Settings can override them.
export const AI_PROVIDERS: AiProviderInfo[] = [
  { id: 'anthropic', label: 'Anthropic (Claude)', defaultModel: 'claude-opus-5-5', keyHint: 'sk-ant-...', needsKey: true },
  { id: 'openai', label: 'OpenAI', defaultModel: 'gpt-5-mini', keyHint: 'sk-...', needsKey: true },
  { id: 'gemini', label: 'Google Gemini', defaultModel: 'gemini-2.5-flash', keyHint: 'AIza...', needsKey: true },
  { id: 'groq', label: 'Groq', defaultModel: 'openai/gpt-oss-120b', keyHint: 'gsk_...', needsKey: true },
  { id: 'openrouter', label: 'OpenRouter', defaultModel: 'anthropic/claude-sonnet-5-5', keyHint: 'sk-or-...', needsKey: true },
  { id: 'custom', label: 'Other (OpenAI-compatible URL)', defaultModel: '', keyHint: 'optional', needsKey: false },
];

const STORAGE_KEY = 'symmetry.aiAgentSettings';
const KEY_STORAGE_KEY = 'symmetry.aiAgentApiKey';

const DEFAULT_SETTINGS: AiAgentSettings = {
  provider: 'anthropic',
  model: '',
  apiKey: '',
  baseUrl: '',
};

export const providerInfo = (provider: AiProvider): AiProviderInfo =>
  AI_PROVIDERS.find((p) => p.id === provider) ?? (AI_PROVIDERS[0] as AiProviderInfo);

const loadSavedSettings = (): Partial<AiAgentSettings> => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
};

export const loadAiAgentSettings = (): AiAgentSettings => {
  const saved = loadSavedSettings();

  // Earlier builds saved the key in localStorage, where it lasted forever.
  // Move it to this session and remove it from disk.
  if (saved.apiKey) {
    sessionStorage.setItem(KEY_STORAGE_KEY, saved.apiKey);
    delete saved.apiKey;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
  }

  return {
    ...DEFAULT_SETTINGS,
    ...saved,
    apiKey: sessionStorage.getItem(KEY_STORAGE_KEY) ?? '',
  };
};

export const saveAiAgentSettings = (settings: AiAgentSettings) => {
  const { apiKey, ...rest } = settings;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rest));
  if (apiKey) {
    sessionStorage.setItem(KEY_STORAGE_KEY, apiKey);
  } else {
    sessionStorage.removeItem(KEY_STORAGE_KEY);
  }
};

/** The model that will actually be used: the typed one or the provider default. */
export const effectiveModel = (settings: AiAgentSettings): string =>
  settings.model.trim() || providerInfo(settings.provider).defaultModel;

/** Why the summary can't run yet, or null when the settings are usable. */
export const missingSetting = (settings: AiAgentSettings): string | null => {
  const info = providerInfo(settings.provider);
  if (info.needsKey && !settings.apiKey.trim()) {
    return `Add your ${info.label} API key in Settings.`;
  }
  if (settings.provider === 'custom') {
    if (!settings.baseUrl.trim()) return 'Set the endpoint URL in Settings.';
    if (!settings.model.trim()) return 'Set a model name in Settings.';
  }
  return null;
};
