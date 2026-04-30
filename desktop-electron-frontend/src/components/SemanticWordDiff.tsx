import React from 'react';
import { AlignedSentencePair, WordToken } from '../models/structured-wiki';

// ---------------------------------------------------------------------------
// Individual token rendering
// ---------------------------------------------------------------------------

const TokenSpan: React.FC<{ token: WordToken }> = ({ token }) => {
  switch (token.type) {
    case 'equal':
      return <span className="text-gray-700">{token.text} </span>;
    case 'insert':
      return (
        <span
          className="bg-blue-100 text-blue-800 rounded px-0.5 mx-0.5 font-medium"
          title="Added in target"
        >
          {token.text}{' '}
        </span>
      );
    case 'delete':
      return (
        <span
          className="bg-red-100 text-red-700 line-through rounded px-0.5 mx-0.5"
          title="Removed from source"
        >
          {token.text}{' '}
        </span>
      );
    case 'replace':
      return (
        <>
          <span
            className="bg-orange-100 text-orange-700 line-through rounded px-0.5 mx-0.5"
            title={`Changed to: ${token.new}`}
          >
            {token.old}
          </span>
          <span className="text-gray-400 mx-0.5 text-xs">→</span>
          <span
            className="bg-orange-200 text-orange-900 font-medium rounded px-0.5 mx-0.5"
            title={`Was: ${token.old}`}
          >
            {token.new}{' '}
          </span>
        </>
      );
    default:
      return null;
  }
};

// ---------------------------------------------------------------------------
// Single sentence-pair row
// ---------------------------------------------------------------------------

const SentencePairRow: React.FC<{ pair: AlignedSentencePair; index: number }> = ({
  pair,
  index,
}) => {
  const pct = Math.round(pair.similarity * 100);
  const barColor =
    pair.similarity >= 0.8
      ? 'bg-green-500'
      : pair.similarity >= 0.5
      ? 'bg-yellow-500'
      : 'bg-red-500';

  // Compute change stats
  const replaceCount = pair.word_diff.filter((t) => t.type === 'replace').length;
  const insertCount = pair.word_diff.filter((t) => t.type === 'insert').length;
  const deleteCount = pair.word_diff.filter((t) => t.type === 'delete').length;
  const hasChanges = replaceCount + insertCount + deleteCount > 0;

  return (
    <div
      className={`rounded-lg border p-3 space-y-2 text-sm ${
        hasChanges
          ? 'border-orange-200 bg-orange-50/30'
          : 'border-green-200 bg-green-50/20'
      }`}
      data-testid={`sentence-pair-${index}`}
    >
      {/* Similarity bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-xs text-gray-500 w-10 text-right">{pct}%</span>
        {hasChanges && (
          <div className="flex gap-1 text-xs">
            {replaceCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-700">
                {replaceCount} replaced
              </span>
            )}
            {insertCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                +{insertCount}
              </span>
            )}
            {deleteCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                −{deleteCount}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Side-by-side sentences */}
      <div className="grid grid-cols-2 gap-3">
        <div className="leading-relaxed text-gray-700">{pair.source_sentence}</div>
        <div className="leading-relaxed">
          {pair.word_diff.map((token, i) => (
            <TokenSpan key={i} token={token} />
          ))}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

const Legend: React.FC = () => (
  <div className="flex flex-wrap gap-3 text-xs text-gray-600 py-2 border-b border-gray-100">
    <span className="font-medium text-gray-500">Legend:</span>
    <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-700">unchanged</span>
    <span className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 line-through">deleted word</span>
    <span className="px-1.5 py-0.5 rounded bg-orange-200 text-orange-900">replaced word</span>
    <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">added word</span>
    <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700 line-through">removed word</span>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface SemanticWordDiffProps {
  pairs: AlignedSentencePair[];
  sourceLang?: string;
  targetLang?: string;
}

const SemanticWordDiff: React.FC<SemanticWordDiffProps> = ({
  pairs,
  sourceLang = 'source',
  targetLang = 'target',
}) => {
  if (pairs.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic py-2">
        No aligned sentence pairs found for this section.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="semantic-word-diff">
      <Legend />
      <div className="grid grid-cols-2 gap-3 text-xs font-semibold text-gray-500 uppercase tracking-wide px-1">
        <span>{sourceLang}</span>
        <span>{targetLang} (with word-level diff)</span>
      </div>
      {pairs.map((pair, i) => (
        <SentencePairRow key={i} pair={pair} index={i} />
      ))}
    </div>
  );
};

export default SemanticWordDiff;
