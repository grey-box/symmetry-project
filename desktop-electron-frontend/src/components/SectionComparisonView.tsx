import React, { useState } from 'react';
import { SectionCompareResponse, SectionDiff, ParagraphDiff } from '../models/structured-wiki';

/** Color-coded status badge for section/paragraph match status */
const StatusBadge: React.FC<{ status: string; similarity?: number }> = ({ status, similarity }) => {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    matched: { bg: 'bg-green-100', text: 'text-green-800', label: 'Matched' },
    missing_in_target: { bg: 'bg-red-100', text: 'text-red-800', label: 'Missing in Target' },
    added_in_target: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Added in Target' },
  };
  const c = config[status] ?? { bg: 'bg-gray-100', text: 'text-gray-800', label: status };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${c.bg} ${c.text}`}>
      {c.label}
      {similarity !== undefined && (
        <span className="ml-1 opacity-75">({(similarity * 100).toFixed(0)}%)</span>
      )}
    </span>
  );
};

/** Similarity bar: a thin colored bar visualizing a 0-1 score */
const SimilarityBar: React.FC<{ score: number }> = ({ score }) => {
  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? 'bg-green-500' : score >= 0.5 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right">{pct}%</span>
    </div>
  );
};

/** Keyword chip displayed in the margin for exclusive concepts */
const KeywordChip: React.FC<{ keyword: string; side: 'source' | 'target' }> = ({ keyword, side }) => {
  const color =
    side === 'source'
      ? 'bg-orange-100 text-orange-700 border-orange-200'
      : 'bg-purple-100 text-purple-700 border-purple-200';
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded border text-[10px] font-mono leading-tight ${color}`}
      title={`Exclusive to ${side} article`}
    >
      {keyword}
    </span>
  );
};

/** Margin column showing exclusive keywords for one side of the diff */
const KeywordMargin: React.FC<{ keywords: string[]; side: 'source' | 'target' }> = ({ keywords, side }) => {
  if (keywords.length === 0) return null;
  const label = side === 'source' ? 'Source-only concepts' : 'Target-only concepts';
  return (
    <div className="mt-2 pt-2 border-t border-dashed border-gray-200">
      <p className="text-[10px] uppercase tracking-wide text-gray-400 mb-1">{label}</p>
      <div className="flex flex-wrap gap-1">
        {keywords.map((kw) => (
          <KeywordChip key={kw} keyword={kw} side={side} />
        ))}
      </div>
    </div>
  );
};

/** Single paragraph diff row */
const ParagraphDiffRow: React.FC<{ diff: ParagraphDiff }> = ({ diff }) => {
  const isMatched = diff.status === 'matched';
  const isMissing = diff.status === 'missing_in_target';

  const srcKeywords = diff.source_exclusive_keywords ?? [];
  const tgtKeywords = diff.target_exclusive_keywords ?? [];

  return (
    <div
      className={`grid grid-cols-2 gap-4 p-3 rounded-md border ${
        isMatched
          ? 'border-green-200 bg-green-50/30'
          : isMissing
          ? 'border-red-200 bg-red-50/30'
          : 'border-blue-200 bg-blue-50/30'
      }`}
    >
      {/* Source paragraph (left) */}
      <div className="text-sm leading-relaxed text-gray-700">
        {diff.source_text ? (
          <>
            <p>{diff.source_text}</p>
            {isMatched && <KeywordMargin keywords={srcKeywords} side="source" />}
          </>
        ) : (
          <p className="italic text-gray-400">No corresponding paragraph in source</p>
        )}
      </div>

      {/* Target paragraph (right) */}
      <div className="text-sm leading-relaxed text-gray-700">
        {diff.target_text ? (
          <>
            <p>{diff.target_text}</p>
            {isMatched && (
              <div className="mt-2 space-y-1">
                <SimilarityBar score={diff.similarity_score} />
                {diff.levenshtein_score !== null && (
                  <div className="text-xs text-gray-400">
                    Levenshtein: {(diff.levenshtein_score * 100).toFixed(0)}%
                  </div>
                )}
                <KeywordMargin keywords={tgtKeywords} side="target" />
              </div>
            )}
          </>
        ) : (
          <p className="italic text-gray-400">No corresponding paragraph in target</p>
        )}
      </div>
    </div>
  );
};

/** Expandable section diff card */
const SectionDiffCard: React.FC<{
  sectionDiff: SectionDiff;
  sourceLanguage: string;
  targetLanguage: string;
  forceExpanded?: boolean | null;
}> = ({
  sectionDiff,
  sourceLanguage,
  targetLanguage,
  forceExpanded,
}) => {
  const [localExpanded, setLocalExpanded] = useState(false);
  const expanded = forceExpanded !== null && forceExpanded !== undefined ? forceExpanded : localExpanded;
  const hasParagraphs = sectionDiff.paragraph_diffs.length > 0;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Section header (clickable) */}
      <button
        onClick={() => setLocalExpanded(!localExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-gray-400 text-sm">{expanded ? '\u25BC' : '\u25B6'}</span>
          <div className="min-w-0">
            <div className="font-medium text-gray-800 truncate">
              {sectionDiff.source_title || sectionDiff.target_title}
            </div>
            {sectionDiff.status === 'matched' && sectionDiff.source_title !== sectionDiff.target_title && (
              <div className="text-xs text-gray-500 truncate">
                {targetLanguage}: {sectionDiff.target_title}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 ml-4">
          {hasParagraphs && (
            <span className="text-xs text-gray-400">{sectionDiff.paragraph_diffs.length} paragraphs</span>
          )}
          <StatusBadge status={sectionDiff.status} similarity={sectionDiff.section_similarity} />
        </div>
      </button>

      {/* Paragraph diffs (expanded) */}
      {expanded && hasParagraphs && (
        <div className="border-t border-gray-200 p-4 space-y-3 bg-gray-50/50">
          {/* Column headers */}
          <div className="grid grid-cols-2 gap-4 text-xs font-medium text-gray-500 uppercase tracking-wide px-3">
            <span>Source ({sourceLanguage})</span>
            <span>Target ({targetLanguage})</span>
          </div>

          {sectionDiff.paragraph_diffs.map((pDiff, idx) => (
            <ParagraphDiffRow key={idx} diff={pDiff} />
          ))}
        </div>
      )}

      {/* Section without paragraphs (missing/added) */}
      {expanded && !hasParagraphs && (
        <div className="border-t border-gray-200 p-4 text-sm text-gray-500 italic">
          {sectionDiff.status === 'missing_in_target'
            ? 'This section exists in the source article but has no counterpart in the target.'
            : 'This section exists only in the target article.'}
        </div>
      )}
    </div>
  );
};

/** ---- Main component ---- */

interface SectionComparisonViewProps {
  comparisonResult: SectionCompareResponse;
}

const SectionComparisonView: React.FC<SectionComparisonViewProps> = ({ comparisonResult }) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [allExpanded, setAllExpanded] = useState<boolean | null>(null);

  const filteredSections =
    filterStatus === 'all'
      ? comparisonResult.section_diffs
      : comparisonResult.section_diffs.filter((s) => s.status === filterStatus);

  const displayNames = new Intl.DisplayNames(['en'], { type: 'language' });
  const sourceLangLabel = displayNames.of(comparisonResult.source_lang) ?? comparisonResult.source_lang;
  const targetLangLabel = displayNames.of(comparisonResult.target_lang) ?? comparisonResult.target_lang;

  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-1">
          Section Comparison: {comparisonResult.source_title} vs {comparisonResult.target_title}
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          {sourceLangLabel} ({comparisonResult.source_lang}) → {targetLangLabel} ({comparisonResult.target_lang})
        </p>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-gray-800">
              {(comparisonResult.overall_similarity * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-gray-500">Overall Similarity</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{comparisonResult.matched_section_count}</div>
            <div className="text-xs text-green-600">Matched</div>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-red-700">{comparisonResult.missing_section_count}</div>
            <div className="text-xs text-red-600">Missing in Target</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-700">{comparisonResult.added_section_count}</div>
            <div className="text-xs text-blue-600">Added in Target</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-gray-800">
              {comparisonResult.source_section_count} / {comparisonResult.target_section_count}
            </div>
            <div className="text-xs text-gray-500">Source / Target Sections</div>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-gray-500">Filter:</span>
        {[
          { value: 'all', label: 'All', count: comparisonResult.section_diffs.length },
          { value: 'matched', label: 'Matched', count: comparisonResult.matched_section_count },
          { value: 'missing_in_target', label: 'Missing', count: comparisonResult.missing_section_count },
          { value: 'added_in_target', label: 'Added', count: comparisonResult.added_section_count },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilterStatus(f.value)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              filterStatus === f.value
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f.label} ({f.count})
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setAllExpanded(true)}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200"
            data-testid="btn-expand-all"
          >
            Expand All
          </button>
          <button
            onClick={() => setAllExpanded(false)}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200"
            data-testid="btn-collapse-all"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Section diff list */}
      <div className="space-y-3">
        {filteredSections.length === 0 ? (
          <div className="text-center py-8 text-gray-400">No sections match the current filter.</div>
        ) : (
          filteredSections.map((sectionDiff, idx) => (
            <SectionDiffCard
              key={`${sectionDiff.source_title}-${sectionDiff.target_title}-${idx}`}
              sectionDiff={sectionDiff}
              sourceLanguage={sourceLangLabel}
              targetLanguage={targetLangLabel}
              forceExpanded={allExpanded}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default SectionComparisonView;
