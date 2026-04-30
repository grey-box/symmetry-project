import React, { useMemo, useState } from 'react';

import {
  Revision,
  RevisionDiffResponse,
  RevisionSectionChange,
  RevisionDetailedDiffResponse,
  RevisionFlag,
} from '../models/structured-wiki';
import { structuredWikiService } from '../services/structuredWikiService';

const formatDate = (iso: string) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

const SectionChangeList: React.FC<{ title: string; items: RevisionSectionChange[]; tone: string }> = ({
  title,
  items,
  tone,
}) => {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className={`rounded-lg border p-4 ${tone}`}>
      <h4 className="font-semibold mb-2">{title} ({items.length})</h4>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {items.map((item) => (
          <div key={item.section_title} className="text-sm">
            <div className="font-medium">{item.section_title}</div>
            <div className="text-xs opacity-80">
              Similarity: {item.similarity_score > 0 ? `${(item.similarity_score * 100).toFixed(0)}%` : 'n/a'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const flagTone = (severity: RevisionFlag['severity']) => {
  if (severity === 'high') {
    return 'bg-red-50 border-red-200 text-red-900';
  }
  if (severity === 'medium') {
    return 'bg-amber-50 border-amber-200 text-amber-900';
  }
  return 'bg-blue-50 border-blue-200 text-blue-900';
};

const ThroughTimeComparison: React.FC = () => {
  const [query, setQuery] = useState('Python (programming language)');
  const [lang, setLang] = useState('en');
  const [limit, setLimit] = useState(20);
  const [includeFlags, setIncludeFlags] = useState(true);

  const [historyLoading, setHistoryLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [oldRevisionId, setOldRevisionId] = useState<number | null>(null);
  const [newRevisionId, setNewRevisionId] = useState<number | null>(null);
  const [diff, setDiff] = useState<RevisionDiffResponse | null>(null);
  const [detailedDiff, setDetailedDiff] = useState<RevisionDetailedDiffResponse | null>(null);

  const sortedRevisions = useMemo(() => {
    return [...revisions].sort((a, b) => {
      const tA = new Date(a.timestamp).getTime();
      const tB = new Date(b.timestamp).getTime();
      return tA - tB;
    });
  }, [revisions]);

  const loadHistory = async (event: React.FormEvent) => {
    event.preventDefault();
    setHistoryLoading(true);
    setError(null);
    setDiff(null);
    setDetailedDiff(null);

    try {
      const response = await structuredWikiService.getRevisionHistory({
        query: query.trim(),
        lang,
        limit,
      });

      setRevisions(response);

      if (response.length >= 2) {
        const asc = [...response].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        );
        setOldRevisionId(asc[0]?.revid ?? null);
        setNewRevisionId(asc[asc.length - 1]?.revid ?? null);
      } else {
        setOldRevisionId(null);
        setNewRevisionId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load revision history');
      setRevisions([]);
      setOldRevisionId(null);
      setNewRevisionId(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  const compareRevisions = async () => {
    if (!oldRevisionId || !newRevisionId) {
      setError('Please select two revisions.');
      return;
    }
    if (oldRevisionId === newRevisionId) {
      setError('Select two different revision IDs.');
      return;
    }

    setCompareLoading(true);
    setError(null);

    try {
      const trimmedQuery = query.trim();
      const parsed = trimmedQuery.includes('://')
        ? structuredWikiService.parseWikipediaUrl(trimmedQuery)
        : null;
      const compareTitle = parsed?.title ?? trimmedQuery;
      const compareLang = parsed?.lang ?? lang;

      const response = await structuredWikiService.getRevisionDiff({
        revid_a: oldRevisionId,
        revid_b: newRevisionId,
        title: compareTitle,
        lang: compareLang,
      });
      setDiff(response);

      const detailedResponse = await structuredWikiService.getRevisionDetailedDiff({
        old_revid: oldRevisionId,
        new_revid: newRevisionId,
        title: compareTitle,
        lang: compareLang,
        include_flags: includeFlags,
      });
      setDetailedDiff(detailedResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare revisions');
      setDiff(null);
      setDetailedDiff(null);
    } finally {
      setCompareLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Through-Time Comparison</h2>
        <p className="text-sm text-gray-500 mb-6">
          Select two revisions of a Wikipedia page and inspect structural evolution over time.
        </p>

        <form onSubmit={loadHistory} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Article Title or URL</label>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Python (programming language)"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
              <input
                value={lang}
                onChange={(e) => setLang(e.target.value.trim().toLowerCase().slice(0, 3))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="en"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Revisions to Load</label>
              <input
                type="number"
                min="2"
                max="100"
                value={limit}
                onChange={(e) => setLimit(Math.max(2, Math.min(100, Number(e.target.value) || 20)))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div className="md:col-span-2">
              <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={includeFlags}
                  onChange={(e) => setIncludeFlags(e.target.checked)}
                  className="h-4 w-4"
                />
                Include revision risk flags (volume, removed sections, lead changes, rapid edits)
              </label>
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button
                type="submit"
                disabled={historyLoading || !query.trim()}
                className="px-5 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {historyLoading ? 'Loading...' : 'Load Revision History'}
              </button>

              <button
                type="button"
                disabled={compareLoading || !oldRevisionId || !newRevisionId}
                onClick={compareRevisions}
                className="px-5 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 disabled:opacity-50"
              >
                {compareLoading ? 'Comparing...' : 'Compare Selected Revisions'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-100 border border-red-300 text-red-700 rounded-md">{error}</div>
      )}

      {sortedRevisions.length > 0 && (
        <div className="bg-white rounded-xl shadow-md p-6 space-y-4">
          <h3 className="text-lg font-semibold">Revision Selection</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Older Revision</label>
              <select
                value={oldRevisionId ?? ''}
                onChange={(e) => setOldRevisionId(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
              >
                <option value="">Select older revision</option>
                {sortedRevisions.map((rev) => (
                  <option key={`old-${rev.revid}`} value={rev.revid}>
                    {rev.revid} - {formatDate(rev.timestamp)} - {rev.user}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Newer Revision</label>
              <select
                value={newRevisionId ?? ''}
                onChange={(e) => setNewRevisionId(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
              >
                <option value="">Select newer revision</option>
                {sortedRevisions.map((rev) => (
                  <option key={`new-${rev.revid}`} value={rev.revid}>
                    {rev.revid} - {formatDate(rev.timestamp)} - {rev.user}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 sticky top-0">
                <tr>
                  <th className="text-left p-2">Revision</th>
                  <th className="text-left p-2">Timestamp</th>
                  <th className="text-left p-2">User</th>
                  <th className="text-left p-2">Comment</th>
                </tr>
              </thead>
              <tbody>
                {sortedRevisions.map((rev) => (
                  <tr key={rev.revid} className="border-t border-gray-100 align-top">
                    <td className="p-2 font-mono">{rev.revid}</td>
                    <td className="p-2">{formatDate(rev.timestamp)}</td>
                    <td className="p-2">{rev.user}</td>
                    <td className="p-2 text-gray-600">{rev.comment || 'No edit comment'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {diff && (
        <div className="bg-white rounded-xl shadow-md p-6 space-y-4">
          <h3 className="text-lg font-semibold">Revision Diff Summary</h3>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-gray-800">{(diff.overall_similarity * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-500">Overall Similarity</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-700">{diff.sections_added.length}</div>
              <div className="text-xs text-green-600">Added Sections</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-700">{diff.sections_removed.length}</div>
              <div className="text-xs text-red-600">Removed Sections</div>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-amber-700">{diff.sections_modified.length}</div>
              <div className="text-xs text-amber-700">Modified Sections</div>
            </div>
            <div className="bg-sky-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-sky-700">{detailedDiff ? detailedDiff.total_chars_old : '-'}</div>
              <div className="text-xs text-sky-700">Chars (old)</div>
            </div>
            <div className="bg-indigo-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-indigo-700">{detailedDiff ? detailedDiff.total_chars_new : '-'}</div>
              <div className="text-xs text-indigo-700">Chars (new)</div>
            </div>
          </div>

          {includeFlags && detailedDiff && (
            <div className="space-y-2">
              <h4 className="font-semibold">Revision Risk Flags</h4>
              {!detailedDiff.flags || detailedDiff.flags.length === 0 ? (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                  No risk flags detected for this revision pair.
                </div>
              ) : (
                <div className="space-y-2">
                  {detailedDiff.flags.map((flag) => (
                    <div key={`${flag.revid}-${flag.reason}-${flag.detail}`} className={`rounded-lg border p-3 ${flagTone(flag.severity)}`}>
                      <div className="text-sm font-semibold uppercase tracking-wide">{flag.reason.replaceAll('_', ' ')}</div>
                      <div className="text-xs opacity-80 mb-1">Severity: {flag.severity}</div>
                      <div className="text-sm">{flag.detail}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <SectionChangeList
              title="Sections Added"
              items={diff.sections_added}
              tone="bg-green-50 border-green-200 text-green-900"
            />
            <SectionChangeList
              title="Sections Removed"
              items={diff.sections_removed}
              tone="bg-red-50 border-red-200 text-red-900"
            />
            <SectionChangeList
              title="Sections Modified"
              items={diff.sections_modified}
              tone="bg-amber-50 border-amber-200 text-amber-900"
            />
          </div>
        </div>
      )}
    </section>
  );
};

export default ThroughTimeComparison;
