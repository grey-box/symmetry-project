import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  AI_PROVIDERS,
  AiAgentSettings,
  AiProvider,
  loadAiAgentSettings,
  providerInfo,
  saveAiAgentSettings,
} from '@/services/aiAgentSettings';

/**
 * Settings card for the AI agent that writes Through-Time revision summaries.
 * For testing: the key is kept in this computer's local storage only.
 */
const AiAgentSettingsCard: React.FC = () => {
  const [saved, setSaved] = useState<AiAgentSettings>(loadAiAgentSettings);
  const [draft, setDraft] = useState<AiAgentSettings>(saved);
  const [showKey, setShowKey] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const info = providerInfo(draft.provider);
  const changed = JSON.stringify(draft) !== JSON.stringify(saved);

  const update = (fields: Partial<AiAgentSettings>) => {
    setDraft((current) => ({ ...current, ...fields }));
    setMessage(null);
  };

  const onSave = () => {
    const cleaned = {
      ...draft,
      apiKey: draft.apiKey.trim(),
      model: draft.model.trim(),
      baseUrl: draft.baseUrl.trim(),
    };
    saveAiAgentSettings(cleaned);
    setSaved(cleaned);
    setDraft(cleaned);
    setMessage('Saved.');
  };

  const onClearKey = () => {
    const cleared = { ...saved, apiKey: '' };
    saveAiAgentSettings(cleared);
    setSaved(cleared);
    setDraft((current) => ({ ...current, apiKey: '' }));
    setMessage('API key removed from this computer.');
  };

  return (
    <section className="bg-white mt-6 rounded-xl shadow-md p-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-base">AI Agent</h2>
          <p className="text-sm">
            Used by the Through-Time tab to summarize what changed between two revisions.
          </p>
        </div>
        <div className="gap-x-4 flex">
          <Button type="button" onClick={onSave} disabled={!changed}>Save</Button>
          <Button type="button" variant="outline" onClick={() => setDraft(saved)} disabled={!changed}>
            Cancel
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Provider
          <select
            value={draft.provider}
            onChange={(e) => update({ provider: e.target.value as AiProvider, model: '' })}
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm font-normal"
            data-testid="ai-provider"
          >
            {AI_PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Model
          <Input
            value={draft.model}
            onChange={(e) => update({ model: e.target.value })}
            placeholder={info.defaultModel || 'model name, e.g. llama3.1'}
            className="font-normal"
            data-testid="ai-model"
          />
          <span className="text-xs font-normal text-gray-500">
            {info.defaultModel
              ? `Leave empty to use ${info.defaultModel}.`
              : "Required. Use the name your server lists."}
          </span>
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          API Key
          <div className="flex gap-2">
            <Input
              type={showKey ? 'text' : 'password'}
              value={draft.apiKey}
              onChange={(e) => update({ apiKey: e.target.value })}
              placeholder={info.keyHint}
              autoComplete="off"
              className="font-normal"
              data-testid="ai-api-key"
            />
            <Button type="button" variant="outline" onClick={() => setShowKey((v) => !v)}>
              {showKey ? 'Hide' : 'Show'}
            </Button>
          </div>
          <span className="text-xs font-normal text-gray-500">
            Stored only on this computer. Sent to the local backend with each summary request,
            which passes it to the provider and never saves it.
          </span>
        </label>

        {draft.provider === 'custom' && (
          <label className="flex flex-col gap-1 text-sm font-medium">
            Endpoint URL
            <Input
              value={draft.baseUrl}
              onChange={(e) => update({ baseUrl: e.target.value })}
              placeholder="http://localhost:11434/v1"
              className="font-normal"
              data-testid="ai-base-url"
            />
            <span className="text-xs font-normal text-gray-500">
              Any server with an OpenAI-compatible /chat/completions endpoint (Ollama, LM Studio, vLLM...).
            </span>
          </label>
        )}
      </div>

      <div className="flex items-center justify-between mt-4 text-sm">
        <span className="text-gray-600">
          {saved.apiKey
            ? `A ${providerInfo(saved.provider).label} key is set until the app closes.`
            : 'No API key set. Keys are not saved between runs.'}
          {message && <span className="ml-2 text-emerald-700">{message}</span>}
        </span>
        {saved.apiKey && (
          <Button type="button" variant="outline" onClick={onClearKey}>Remove key</Button>
        )}
      </div>
    </section>
  );
};

export default AiAgentSettingsCard;
