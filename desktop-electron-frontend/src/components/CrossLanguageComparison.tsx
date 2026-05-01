import React, { useState, useEffect, useRef } from 'react';

import SectionComparisonView from './SectionComparisonView';
import SectionHeatmap from './SectionHeatmap';
import SideBySideComparisonView from './SideBySideComparisonView';
import { SectionCompareResponse, ParagraphDiffResponse } from '../models/structured-wiki';
import { structuredWikiService } from '../services/structuredWikiService';

type TargetLanguage = { lang: string; title: string };

const CrossLanguageComparison: React.FC = () => {
  // ── Source (URL-driven) ───────────────────────────────────────────────────
  const [sourceUrl, setSourceUrl] = useState('');
  const [sourceTitle, setSourceTitle] = useState('');
  const [sourceLang, setSourceLang] = useState('');
  const [availableTargets, setAvailableTargets] = useState<TargetLanguage[]>([]);
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  // ── Target ────────────────────────────────────────────────────────────────
  const [targetLang, setTargetLang] = useState('');
  const [targetQuery, setTargetQuery] = useState('');
  const [targetEditedManually, setTargetEditedManually] = useState(false);

  // ── Options & results ─────────────────────────────────────────────────────
  const [threshold, setThreshold] = useState(0.65);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SectionCompareResponse | null>(null);
  const [paragraphDiff, setParagraphDiff] = useState<ParagraphDiffResponse | null>(null);
  const [paragraphDiffLoading, setParagraphDiffLoading] = useState(false);
  const [showSideBySide, setShowSideBySide] = useState(false);

  // Debounce URL lookup (500 ms after last keystroke)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const trimmed = sourceUrl.trim();

    // Only trigger when it looks like a Wikipedia URL
    if (!trimmed.includes('wikipedia.org')) {
      setSourceTitle('');
      setSourceLang('');
      setAvailableTargets([]);
      setTargetLang('');
      if (!targetEditedManually) setTargetQuery('');
      setUrlError(null);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setUrlLoading(true);
      setUrlError(null);
      try {
        const data = await structuredWikiService.getArticleLanguages(trimmed);
        setSourceLang(data.source_lang);
        setSourceTitle(data.source_title);
        setAvailableTargets(data.available_targets);
        // Reset target when source changes
        setTargetLang('');
        setTargetQuery('');
        setTargetEditedManually(false);
      } catch (err) {
        setUrlError(err instanceof Error ? err.message : 'Could not load article languages');
        setSourceTitle('');
        setSourceLang('');
        setAvailableTargets([]);
      } finally {
        setUrlLoading(false);
      }
    }, 500);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [sourceUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // When target language changes, auto-fill the target article title (unless edited manually)
  const onTargetLangChange = (lang: string) => {
    setTargetLang(lang);
    if (!targetEditedManually) {
      const match = availableTargets.find((t) => t.lang === lang);
      setTargetQuery(match ? match.title : '');
    }
  };

  const onTargetQueryChange = (value: string) => {
    setTargetQuery(value);
    setTargetEditedManually(true);
  };

  const onCompare = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await structuredWikiService.compareSections({
        source_query: sourceUrl.trim() || sourceTitle.trim(),
        target_query: targetQuery.trim(),
        source_lang: sourceLang,
        target_lang: targetLang,
        similarity_threshold: threshold,
      });
      setResult(response);
      setParagraphDiff(null);
      setShowSideBySide(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const loadDetailedAnalysis = async () => {
    setParagraphDiffLoading(true);
    try {
      const response = await structuredWikiService.getParagraphDiff({
        source_query: sourceUrl.trim() || sourceTitle.trim(),
        target_query: targetQuery.trim(),
        source_lang: sourceLang,
        target_lang: targetLang,
        similarity_threshold: threshold,
      });
      setParagraphDiff(response);
      setShowSideBySide(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Paragraph diff failed');
    } finally {
      setParagraphDiffLoading(false);
    }
  };

  const exportJson = () => {
    const data = paragraphDiff ?? result;
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison-${sourceTitle.replace(/\s+/g, '_') || 'source'}-${targetQuery.replace(/\s+/g, '_') || 'target'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const heatmapSections = result?.section_diffs
    .filter((s) => s.status === 'matched')
    .map((s) => ({ title: s.source_title || s.target_title, similarity: s.section_similarity })) ?? [];

  const canCompare = !loading && !!sourceLang && !!sourceTitle && !!targetLang && !!targetQuery.trim();

  return (
    <section className="space-y-6">
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Cross-Language Semantic Diff</h2>
        <p className="text-sm text-gray-500 mb-6">
          Compare two Wikipedia pages section-by-section and paragraph-by-paragraph.
        </p>

        <form onSubmit={onCompare} className="space-y-4">
          {/* ── Source Article URL ─────────────────────────────────────────── */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Article URL
            </label>
            <div className="relative">
              <input
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md pr-10"
                placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)"
                required
              />
              {urlLoading && (
                <span className="absolute right-3 top-2.5 text-gray-400 text-xs animate-pulse">
                  Loading…
                </span>
              )}
            </div>
            {urlError && (
              <p className="mt-1 text-xs text-red-600">{urlError}</p>
            )}
            {sourceTitle && !urlLoading && (
              <p className="mt-1 text-xs text-gray-500">
                Detected: <span className="font-medium text-gray-700">{sourceTitle}</span>
                {' '}
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  {sourceLang}
                </span>
                {' · '}{availableTargets.length} target language{availableTargets.length !== 1 ? 's' : ''} available
              </p>
            )}
          </div>

          {/* ── Target Language + Article ──────────────────────────────────── */}
          {availableTargets.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Language
                </label>
                <select
                  value={targetLang}
                  onChange={(e) => onTargetLangChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                  required
                >
                  <option value="">— Select a language —</option>
                  {availableTargets.map((t) => (
                    <option key={t.lang} value={t.lang}>
                      {t.lang.toUpperCase()} — {t.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Article
                  {targetEditedManually && targetLang && (
                    <button
                      type="button"
                      onClick={() => {
                        const match = availableTargets.find((t) => t.lang === targetLang);
                        if (match) {
                          setTargetQuery(match.title);
                          setTargetEditedManually(false);
                        }
                      }}
                      className="ml-2 text-xs text-blue-600 hover:underline font-normal"
                    >
                      Reset to detected title
                    </button>
                  )}
                </label>
                <input
                  value={targetQuery}
                  onChange={(e) => onTargetQueryChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Auto-filled from selected language"
                  required
                />
              </div>
            </div>
          )}

          {/* ── Threshold ─────────────────────────────────────────────────── */}
          {availableTargets.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Similarity Threshold
                </label>
                <input
                  type="number"
                  min="0.1"
                  max="0.99"
                  step="0.01"
                  value={threshold}
                  onChange={(e) =>
                    setThreshold(Math.max(0.1, Math.min(0.99, Number(e.target.value) || 0.65)))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={!canCompare}
              className="px-5 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Comparing...' : 'Compare Sections'}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-100 border border-red-300 text-red-700 rounded-md">{error}</div>
      )}

      {result && (
        <>
          {/* Heatmap */}
          {heatmapSections.length > 0 && (
            <div className="bg-white rounded-xl shadow-md p-6">
              <SectionHeatmap sections={heatmapSections} />
            </div>
          )}

          {/* Action bar */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={loadDetailedAnalysis}
              disabled={paragraphDiffLoading || !!paragraphDiff}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
              data-testid="btn-detailed-analysis"
            >
              {paragraphDiffLoading ? 'Loading word-level diff…' : paragraphDiff ? 'Word-level diff loaded' : 'Detailed Analysis (word-level diff)'}
            </button>

            {paragraphDiff && (
              <button
                onClick={() => setShowSideBySide((v) => !v)}
                className="px-4 py-2 bg-gray-700 text-white text-sm rounded-md hover:bg-gray-800"
                data-testid="btn-toggle-side-by-side"
              >
                {showSideBySide ? 'Hide Side-by-Side View' : 'Show Side-by-Side View'}
              </button>
            )}

            <button
              onClick={exportJson}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200 border border-gray-300"
              data-testid="btn-export-json"
            >
              Export JSON
            </button>
          </div>

          {/* Side-by-side view (word-level diff) */}
          {paragraphDiff && showSideBySide && (
            <div className="bg-white rounded-xl shadow-md overflow-hidden">
              <SideBySideComparisonView
                sourceTitle={paragraphDiff.source_title}
                targetTitle={paragraphDiff.target_title}
                sourceLang={paragraphDiff.source_lang}
                targetLang={paragraphDiff.target_lang}
                sections={paragraphDiff.sections}
              />
            </div>
          )}

          {/* Standard section comparison view */}
          <SectionComparisonView comparisonResult={result} />
        </>
      )}
    </section>
  );
};

export default CrossLanguageComparison;
