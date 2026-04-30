import React, { useCallback } from 'react';
import { Revision } from '../models/structured-wiki';

interface RevisionTimelineProps {
  revisions: Revision[];
  selectedOld: number | null;
  selectedNew: number | null;
  onChange: (oldRevId: number | null, newRevId: number | null) => void;
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function sizeDeltaLabel(rev: Revision, prev: Revision | undefined): string {
  if (!prev) return '';
  const delta = rev.size - prev.size;
  if (delta === 0) return '±0';
  return delta > 0 ? `+${delta}` : `${delta}`;
}

function sizeDeltaColor(rev: Revision, prev: Revision | undefined): string {
  if (!prev) return 'text-gray-400';
  const delta = rev.size - prev.size;
  if (delta > 200) return 'text-green-600';
  if (delta < -200) return 'text-red-600';
  return 'text-gray-500';
}

const RevisionTimeline: React.FC<RevisionTimelineProps> = ({
  revisions,
  selectedOld,
  selectedNew,
  onChange,
}) => {
  // Revisions arrive newest-first from the Wikipedia API; display oldest → newest left → right
  const sorted = [...revisions].reverse();

  const handleClick = useCallback(
    (revid: number) => {
      if (selectedNew === revid) {
        // Deselect new
        onChange(selectedOld, null);
      } else if (selectedOld === revid) {
        // Deselect old
        onChange(null, selectedNew);
      } else if (selectedOld === null) {
        onChange(revid, selectedNew);
      } else if (selectedNew === null) {
        // Ensure old < new in timeline order
        const oldIdx = sorted.findIndex((r) => r.revid === selectedOld);
        const newIdx = sorted.findIndex((r) => r.revid === revid);
        if (newIdx > oldIdx) {
          onChange(selectedOld, revid);
        } else {
          onChange(revid, selectedOld);
        }
      } else {
        // Replace whichever selection is closer in index
        const clickIdx = sorted.findIndex((r) => r.revid === revid);
        const oldIdx = sorted.findIndex((r) => r.revid === selectedOld);
        const newIdx = sorted.findIndex((r) => r.revid === selectedNew);
        if (Math.abs(clickIdx - oldIdx) <= Math.abs(clickIdx - newIdx)) {
          // Replace old marker, keep correct ordering
          if (clickIdx < newIdx) {
            onChange(revid, selectedNew);
          } else {
            onChange(selectedNew, revid);
          }
        } else {
          if (clickIdx > oldIdx) {
            onChange(selectedOld, revid);
          } else {
            onChange(revid, selectedOld);
          }
        }
      }
    },
    [selectedOld, selectedNew, sorted, onChange]
  );

  if (sorted.length === 0) {
    return <p className="text-sm text-gray-400 italic">No revisions loaded.</p>;
  }

  return (
    <div className="space-y-3" data-testid="revision-timeline">
      {/* Instructions */}
      <p className="text-xs text-gray-500">
        Click a dot to set <span className="text-blue-600 font-medium">earlier revision</span> then{' '}
        <span className="text-green-600 font-medium">later revision</span> for comparison.
      </p>

      {/* Timeline track */}
      <div className="relative">
        {/* Connecting line */}
        <div className="absolute top-4 left-4 right-4 h-0.5 bg-gray-200" />

        {/* Dots */}
        <div className="flex items-start overflow-x-auto pb-2 gap-0">
          {sorted.map((rev, idx) => {
            const prev = sorted[idx - 1];
            const isOld = rev.revid === selectedOld;
            const isNew = rev.revid === selectedNew;
            const isBetween =
              selectedOld !== null &&
              selectedNew !== null &&
              (() => {
                const oIdx = sorted.findIndex((r) => r.revid === selectedOld);
                const nIdx = sorted.findIndex((r) => r.revid === selectedNew);
                return idx > oIdx && idx < nIdx;
              })();

            const dotClass = isOld
              ? 'bg-blue-500 ring-2 ring-blue-300 scale-125'
              : isNew
              ? 'bg-green-500 ring-2 ring-green-300 scale-125'
              : isBetween
              ? 'bg-indigo-200'
              : 'bg-gray-300 hover:bg-gray-400';

            return (
              <button
                key={rev.revid}
                onClick={() => handleClick(rev.revid)}
                className="relative flex flex-col items-center flex-shrink-0 w-14 group focus:outline-none"
                title={`${formatTimestamp(rev.timestamp)}\n${rev.user}${rev.comment ? `\n${rev.comment}` : ''}`}
                aria-label={`Revision ${rev.revid} by ${rev.user} at ${formatTimestamp(rev.timestamp)}${isOld ? ' (selected as earlier)' : isNew ? ' (selected as later)' : ''}`}
                data-testid={`revision-dot-${rev.revid}`}
              >
                {/* Marker label */}
                {(isOld || isNew) && (
                  <span
                    className={`
                      absolute -top-5 text-[10px] font-bold px-1 rounded
                      ${isOld ? 'text-blue-600 bg-blue-50' : 'text-green-600 bg-green-50'}
                    `}
                  >
                    {isOld ? 'A' : 'B'}
                  </span>
                )}

                {/* Dot */}
                <div
                  className={`
                    w-3.5 h-3.5 rounded-full z-10 transition-all duration-150 cursor-pointer
                    ${dotClass}
                  `}
                />

                {/* Size delta */}
                <span className={`text-[9px] mt-0.5 ${sizeDeltaColor(rev, prev)}`}>
                  {sizeDeltaLabel(rev, prev)}
                </span>

                {/* Tooltip on hover (visible in overflow context) */}
                <span
                  className="
                    pointer-events-none absolute top-5 left-1/2 -translate-x-1/2 mt-1
                    hidden group-hover:block group-focus:block
                    bg-gray-900 text-white text-[10px] rounded px-2 py-1 z-20 shadow-lg
                    whitespace-nowrap
                  "
                >
                  <span className="block font-semibold">{rev.user}</span>
                  <span className="block opacity-80">{formatTimestamp(rev.timestamp)}</span>
                  {rev.comment && (
                    <span className="block opacity-60 max-w-[160px] truncate">{rev.comment}</span>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selection summary */}
      {(selectedOld !== null || selectedNew !== null) && (
        <div className="flex gap-3 text-xs">
          {selectedOld !== null && (
            <span className="px-2 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200">
              A: rev {selectedOld}
              {' — '}
              {formatTimestamp(
                sorted.find((r) => r.revid === selectedOld)?.timestamp ?? ''
              )}
            </span>
          )}
          {selectedNew !== null && (
            <span className="px-2 py-1 rounded bg-green-50 text-green-700 border border-green-200">
              B: rev {selectedNew}
              {' — '}
              {formatTimestamp(
                sorted.find((r) => r.revid === selectedNew)?.timestamp ?? ''
              )}
            </span>
          )}
          {selectedOld !== null && selectedNew !== null && (
            <button
              onClick={() => onChange(null, null)}
              className="ml-auto px-2 py-1 text-gray-500 hover:text-gray-700 underline"
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default RevisionTimeline;
