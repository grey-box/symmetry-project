import React, { useState } from 'react';

import SectionComparisonView from './SectionComparisonView';
import SectionHeatmap from './SectionHeatmap';
import SideBySideComparisonView from './SideBySideComparisonView';
import { SectionCompareResponse, ParagraphDiffResponse } from '../models/structured-wiki';
import { structuredWikiService } from '../services/structuredWikiService';

const LANGUAGE_OPTIONS = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'French' },
  { code: 'es', label: 'Spanish' },
  { code: 'de', label: 'German' },
  { code: 'it', label: 'Italian' },
  { code: 'pt', label: 'Portuguese' },
  { code: 'ru', label: 'Russian' },
  { code: 'ja', label: 'Japanese' },
  { code: 'zh', label: 'Chinese' },
];

const CrossLanguageComparison: React.FC = () => {
  const [sourceQuery, setSourceQuery] = useState('Python (programming language)');
  const [targetQuery, setTargetQuery] = useState('Python (langage)');
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('fr');
  const [threshold, setThreshold] = useState(0.65);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SectionCompareResponse | null>(null);
  const [paragraphDiff, setParagraphDiff] = useState<ParagraphDiffResponse | null>(null);
  const [paragraphDiffLoading, setParagraphDiffLoading] = useState(false);
  const [showSideBySide, setShowSideBySide] = useState(false);

  const onCompare = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await structuredWikiService.compareSections({
        source_query: sourceQuery.trim(),
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
        source_query: sourceQuery.trim(),
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
    a.download = `comparison-${sourceQuery.replace(/\s+/g, '_')}-${targetQuery.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const heatmapSections = result?.section_diffs
    .filter((s) => s.status === 'matched')
    .map((s) => ({ title: s.source_title || s.target_title, similarity: s.section_similarity })) ?? [];

  return (
    <section className="space-y-6">
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Cross-Language Semantic Diff</h2>
        <p className="text-sm text-gray-500 mb-6">
          Compare two Wikipedia pages section-by-section and paragraph-by-paragraph.
        </p>

        <form onSubmit={onCompare} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Source Article</label>
              <input
                value={sourceQuery}
                onChange={(e) => setSourceQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Python (programming language)"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Article</label>
              <input
                value={targetQuery}
                onChange={(e) => setTargetQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Python (langage)"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Source Language</label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
              >
                {LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.code} value={lang.code}>{lang.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Language</label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
              >
                {LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.code} value={lang.code}>{lang.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Similarity Threshold</label>
              <input
                type="number"
                min="0.1"
                max="0.99"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(Math.max(0.1, Math.min(0.99, Number(e.target.value) || 0.65)))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading || !sourceQuery.trim() || !targetQuery.trim()}
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
