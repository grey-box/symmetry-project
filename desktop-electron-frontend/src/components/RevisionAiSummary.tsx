import React, { useMemo, useState } from 'react';

import {
  AiConcern,
  AiKeyChange,
  AiSemanticShift,
  AiSignificance,
  RevisionAiSummaryResponse,
} from '../models/structured-wiki';
import { useSessionState } from '../lib/sessionState';

// ---------------------------------------------------------------------------
// Colors and small helpers
// ---------------------------------------------------------------------------

const impactTone: Record<string, string> = {
  minor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  moderate: 'bg-amber-100 text-amber-800 border-amber-200',
  substantial: 'bg-red-100 text-red-800 border-red-200',
};

const changeTypeTone: Record<AiKeyChange['change_type'], string> = {
  added: 'bg-green-100 text-green-800',
  removed: 'bg-red-100 text-red-800',
  reworded: 'bg-sky-100 text-sky-800',
  expanded: 'bg-teal-100 text-teal-800',
  condensed: 'bg-orange-100 text-orange-800',
  moved: 'bg-indigo-100 text-indigo-800',
  recontextualized: 'bg-purple-100 text-purple-800',
};

const LEVELS: AiSignificance[] = ['high', 'medium', 'low'];

const levelStyle: Record<AiSignificance, { dot: string; group: string; label: string }> = {
  high: { dot: 'bg-red-500', group: 'border-red-200 bg-red-50/40', label: 'High' },
  medium: { dot: 'bg-amber-400', group: 'border-amber-200 bg-amber-50/40', label: 'Medium' },
  low: { dot: 'bg-gray-300', group: 'border-gray-200 bg-gray-50/40', label: 'Low' },
};

const label = (value: string) => value.replace(/_/g, ' ');

// Section names from the AI aren't always written the same way.
const sectionKey = (section: string) => section.trim().toLowerCase() || 'article-wide';

const firstSentence = (text: string) => {
  const match = text.match(/^.*?[.!?](\s|$)/);
  return (match ? match[0] : text).trim();
};

const Chip: React.FC<{ className: string; children: React.ReactNode }> = ({ className, children }) => (
  <span className={`inline-block shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${className}`}>
    {children}
  </span>
);

const Dot: React.FC<{ level: AiSignificance }> = ({ level }) => (
  <span className={`inline-block size-2.5 shrink-0 rounded-full ${levelStyle[level].dot}`} title={`${level} significance`} />
);

/** A collapsible group with a count, using the native <details> element. */
const Group: React.FC<{
  title: React.ReactNode;
  count: number;
  open?: boolean;
  className?: string;
  children: React.ReactNode;
}> = ({ title, count, open = false, className = 'border-gray-200', children }) => (
  <details open={open} className={`group rounded-lg border ${className}`}>
    <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 select-none">
      <span className="text-gray-400 transition-transform group-open:rotate-90">▶</span>
      <span className="font-medium text-gray-800">{title}</span>
      <span className="text-xs text-gray-500">({count})</span>
    </summary>
    <div className="space-y-2 px-4 pb-3">{children}</div>
  </details>
);

// ---------------------------------------------------------------------------
// Rows
// ---------------------------------------------------------------------------

const ChangeRow: React.FC<{ change: AiKeyChange; showSection?: boolean }> = ({ change, showSection = true }) => {
  const [showQuotes, setShowQuotes] = useState(false);
  const hasQuotes = Boolean(change.old_excerpt || change.new_excerpt);
  return (
    <div className="rounded-md border border-gray-200 bg-white p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Dot level={change.significance} />
        <Chip className={changeTypeTone[change.change_type] ?? 'bg-gray-100 text-gray-700'}>
          {label(change.change_type)}
        </Chip>
        {showSection && <span className="text-sm font-medium text-gray-700">{change.section}</span>}
        {hasQuotes && (
          <button
            type="button"
            onClick={() => setShowQuotes((v) => !v)}
            className="ml-auto text-xs text-blue-600 hover:underline"
          >
            {showQuotes ? 'Hide quotes' : 'Show before / after'}
          </button>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-800">{change.description}</p>
      {showQuotes && (
        <div className="mt-2 space-y-1 text-sm">
          {change.old_excerpt && (
            <div className="rounded border-l-4 border-red-300 bg-red-50 px-2 py-1 text-red-900">
              <span className="mr-1 text-xs font-semibold text-red-700">Before:</span>
              <span className="line-through decoration-red-300">{change.old_excerpt}</span>
            </div>
          )}
          {change.new_excerpt && (
            <div className="rounded border-l-4 border-green-300 bg-green-50 px-2 py-1 text-green-900">
              <span className="mr-1 text-xs font-semibold text-green-700">After:</span>
              {change.new_excerpt}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ConcernRow: React.FC<{ concern: AiConcern; showSection?: boolean }> = ({ concern, showSection = true }) => (
  <div className="rounded-md border border-gray-200 bg-white p-3">
    <div className="flex flex-wrap items-center gap-2">
      <Dot level={concern.severity} />
      <Chip className="bg-slate-100 text-slate-700">{label(concern.category)}</Chip>
      {showSection && concern.section && (
        <span className="text-sm font-medium text-gray-700">{concern.section}</span>
      )}
    </div>
    <p className="mt-1 text-sm text-gray-800">{concern.explanation}</p>
    {concern.evidence && (
      <p className="mt-1 border-l-2 border-gray-300 pl-2 text-xs italic text-gray-600">{concern.evidence}</p>
    )}
  </div>
);

const ShiftRow: React.FC<{ shift: AiSemanticShift }> = ({ shift }) => (
  <div className="rounded-md border border-purple-100 bg-white p-3 text-sm">
    <div className="font-medium text-purple-900">{shift.topic}</div>
    <div className="mt-1 grid grid-cols-[1fr_auto_1fr] items-start gap-2 text-gray-800">
      <span className="text-gray-600">{shift.before}</span>
      <span className="text-purple-400">→</span>
      <span>{shift.after}</span>
    </div>
    <div className="mt-1 text-xs text-gray-500">{shift.why_it_matters}</div>
  </div>
);

// ---------------------------------------------------------------------------
// Views
// ---------------------------------------------------------------------------

/** Changes and concerns in collapsible groups by significance; high starts open. */
const ByImportance: React.FC<{ changes: AiKeyChange[]; concerns: AiConcern[] }> = ({ changes, concerns }) => (
  <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
    <div className="space-y-2">
      <h4 className="font-semibold">Changes</h4>
      {changes.length === 0 && <p className="text-sm text-gray-500">No notable changes listed.</p>}
      {LEVELS.map((level) => {
        const items = changes.filter((c) => c.significance === level);
        if (items.length === 0) return null;
        return (
          <Group
            key={level}
            title={`${levelStyle[level].label} significance`}
            count={items.length}
            open={level === 'high'}
            className={levelStyle[level].group}
          >
            {items.map((change, i) => <ChangeRow key={i} change={change} />)}
          </Group>
        );
      })}
    </div>

    <div className="space-y-2">
      <h4 className="font-semibold">Edits Worth a Closer Look</h4>
      {concerns.length === 0 ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          The AI found nothing concerning in these changes.
        </div>
      ) : (
        LEVELS.map((level) => {
          const items = concerns.filter((c) => c.severity === level);
          if (items.length === 0) return null;
          return (
            <Group
              key={level}
              title={`${levelStyle[level].label} severity`}
              count={items.length}
              open={level !== 'low'}
              className={levelStyle[level].group}
            >
              {items.map((concern, i) => <ConcernRow key={i} concern={concern} />)}
            </Group>
          );
        })
      )}
    </div>
  </div>
);

/** Everything that happened to one section together, most affected sections first. */
const BySection: React.FC<{ changes: AiKeyChange[]; concerns: AiConcern[] }> = ({ changes, concerns }) => {
  const sections = useMemo(() => {
    const rank = (level: AiSignificance) => LEVELS.indexOf(level);
    const groups = new Map<string, { name: string; changes: AiKeyChange[]; concerns: AiConcern[]; top: number }>();
    const groupFor = (section: string) => {
      const key = sectionKey(section);
      if (!groups.has(key)) {
        groups.set(key, { name: section.trim() || 'Article-wide', changes: [], concerns: [], top: LEVELS.length });
      }
      return groups.get(key)!;
    };
    changes.forEach((c) => {
      const g = groupFor(c.section);
      g.changes.push(c);
      g.top = Math.min(g.top, rank(c.significance));
    });
    concerns.forEach((c) => {
      const g = groupFor(c.section);
      g.concerns.push(c);
      g.top = Math.min(g.top, rank(c.severity));
    });
    return [...groups.values()].sort(
      (a, b) => a.top - b.top || b.changes.length + b.concerns.length - (a.changes.length + a.concerns.length),
    );
  }, [changes, concerns]);

  return (
    <div className="space-y-2">
      {sections.map((section) => {
        const level = LEVELS[section.top] ?? 'low';
        return (
          <Group
            key={section.name}
            title={
              <span className="inline-flex items-center gap-2">
                <Dot level={level} />
                {section.name}
                {section.concerns.length > 0 && (
                  <span className="rounded bg-red-100 px-1.5 text-xs font-normal text-red-700">
                    {section.concerns.length} to review
                  </span>
                )}
              </span>
            }
            count={section.changes.length + section.concerns.length}
            open={level === 'high'}
            className={levelStyle[level].group}
          >
            {section.changes.map((change, i) => <ChangeRow key={`c${i}`} change={change} showSection={false} />)}
            {section.concerns.map((concern, i) => <ConcernRow key={`k${i}`} concern={concern} showSection={false} />)}
          </Group>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Whole summary
// ---------------------------------------------------------------------------

const RevisionAiSummary: React.FC<{ result: RevisionAiSummaryResponse }> = ({ result }) => {
  const { summary, evidence_stats: stats } = result;
  const [view, setView] = useSessionState<'importance' | 'section'>('throughTime.aiView', 'importance');

  const highChanges = summary.key_changes.filter((c) => c.significance === 'high');
  const highConcerns = summary.concerns.filter((c) => c.severity === 'high');
  const countBy = <T,>(items: T[], pick: (item: T) => AiSignificance) =>
    LEVELS.map((level) => items.filter((item) => pick(item) === level).length);
  const changeCounts = countBy(summary.key_changes, (c) => c.significance);
  const concernCounts = countBy(summary.concerns, (c) => c.severity);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `revision-ai-summary-${result.old_revid}-${result.new_revid}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="revision-ai-summary">
      {/* At a glance */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${impactTone[summary.overall_impact]}`}>
            {summary.overall_impact} change
          </span>
          <span className="text-xs text-gray-500">
            {result.model === 'none' ? 'No AI call needed' : `${result.provider} · ${result.model}`}
            {result.input_tokens != null && result.output_tokens != null &&
              ` · ${result.input_tokens.toLocaleString()} in / ${result.output_tokens.toLocaleString()} out tokens`}
          </span>
          <button
            onClick={exportJson}
            className="ml-auto px-3 py-1.5 text-sm bg-white text-gray-700 rounded-md hover:bg-gray-100 border border-gray-300"
          >
            Export JSON
          </button>
        </div>
        <h4 className="text-lg font-semibold text-gray-900">{summary.headline}</h4>
        <p className="text-sm text-gray-700 leading-relaxed">{summary.overview}</p>

        {(highChanges.length > 0 || highConcerns.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            {highChanges.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500 mb-1">Biggest changes</div>
                <ul className="space-y-1 text-sm text-gray-800">
                  {highChanges.slice(0, 5).map((c, i) => (
                    <li key={i} className="flex gap-2">
                      <Dot level="high" />
                      <span><span className="font-medium">{c.section}:</span> {firstSentence(c.description)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {highConcerns.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase text-gray-500 mb-1">Needs review first</div>
                <ul className="space-y-1 text-sm text-gray-800">
                  {highConcerns.slice(0, 5).map((c, i) => (
                    <li key={i} className="flex gap-2">
                      <Dot level="high" />
                      <span><span className="font-medium capitalize">{label(c.category)}:</span> {firstSentence(c.explanation)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-gray-200 pt-2 text-xs text-gray-600">
          <span>
            <span className="font-semibold">{stats.paragraphs_modified}</span> modified ·{' '}
            <span className="font-semibold">{stats.paragraphs_added}</span> added ·{' '}
            <span className="font-semibold">{stats.paragraphs_removed}</span> removed paragraphs
          </span>
          <span>
            <span className="font-semibold">{stats.sections_added + stats.sections_removed}</span> sections added/removed
          </span>
          <span>
            <span className="font-semibold">+{stats.entities_added} / −{stats.entities_removed}</span> linked entities
          </span>
          <span><span className="font-semibold">{stats.edits_between}</span> edits in between</span>
          <span>
            Changes: {changeCounts[0]} high, {changeCounts[1]} medium, {changeCounts[2]} low · Concerns:{' '}
            {concernCounts[0]} high, {concernCounts[1]} medium, {concernCounts[2]} low
          </span>
        </div>
        {stats.changes_left_out > 0 && (
          <p className="text-xs text-gray-500">
            {stats.changes_left_out} smaller paragraph changes were left out of what the AI read, to keep the request a reasonable size.
          </p>
        )}
      </div>

      {/* Details, grouped */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Group by:</span>
          {(['importance', 'section'] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setView(option)}
              className={`rounded-md px-3 py-1 text-sm capitalize ${
                view === option ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {option}
            </button>
          ))}
        </div>
        {view === 'importance' ? (
          <ByImportance changes={summary.key_changes} concerns={summary.concerns} />
        ) : (
          <BySection changes={summary.key_changes} concerns={summary.concerns} />
        )}
      </div>

      {/* Meaning shifts */}
      {summary.semantic_shifts.length > 0 && (
        <Group
          title={<span className="font-semibold">Shifts in Meaning</span>}
          count={summary.semantic_shifts.length}
          open
          className="border-purple-200 bg-purple-50/30"
        >
          {summary.semantic_shifts.map((shift, i) => <ShiftRow key={i} shift={shift} />)}
        </Group>
      )}

      {/* Entities */}
      {summary.entity_changes.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-semibold">Linked Entities</h4>
          <div className="flex flex-wrap gap-2">
            {summary.entity_changes.map((entity, i) => {
              const tone =
                entity.change === 'added'
                  ? 'border-green-200 bg-green-50 text-green-900'
                  : entity.change === 'removed'
                    ? 'border-red-200 bg-red-50 text-red-900'
                    : 'border-purple-200 bg-purple-50 text-purple-900';
              const sign = entity.change === 'added' ? '+' : entity.change === 'removed' ? '−' : '↻';
              return (
                <div key={i} className={`rounded-md border px-3 py-1.5 text-sm ${tone}`} title={entity.note}>
                  <span className="font-bold mr-1">{sign}</span>
                  {entity.entity}
                  {entity.wikidata_id && (
                    <a
                      href={`https://www.wikidata.org/wiki/${entity.wikidata_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-1 font-mono text-xs underline opacity-70"
                    >
                      {entity.wikidata_id}
                    </a>
                  )}
                  {entity.note && <div className="text-xs opacity-80">{entity.note}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Checklist */}
      {summary.things_to_verify.length > 0 && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4">
          <h4 className="font-semibold text-sky-900 mb-2">Things to Verify</h4>
          <ul className="list-disc pl-5 space-y-1 text-sm text-sky-900">
            {summary.things_to_verify.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Written by an AI from the LaBSE paragraph comparison, Wikidata links and edit summaries. Check important points against the revisions themselves.
      </p>
    </div>
  );
};

export default RevisionAiSummary;
