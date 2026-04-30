import React, { useId } from 'react';

interface HeatmapCell {
  title: string;
  similarity: number;
}

interface SectionHeatmapProps {
  sections: HeatmapCell[];
  onCellClick?: (title: string) => void;
}

/**
 * Returns a Tailwind background class interpolating red → yellow → green
 * based on the 0–1 similarity score.
 */
function similarityColor(score: number): string {
  if (score >= 0.85) return 'bg-green-500';
  if (score >= 0.70) return 'bg-green-400';
  if (score >= 0.55) return 'bg-yellow-400';
  if (score >= 0.40) return 'bg-orange-400';
  return 'bg-red-500';
}

function textOnColor(score: number): string {
  return score >= 0.55 ? 'text-white' : 'text-white';
}

const SectionHeatmap: React.FC<SectionHeatmapProps> = ({ sections, onCellClick }) => {
  const id = useId();

  if (sections.length === 0) return null;

  return (
    <div className="space-y-2" data-testid="section-heatmap">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700">Section Similarity Heatmap</h4>
        {/* Color scale legend */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <span>0%</span>
          <div className="flex rounded overflow-hidden h-3 w-24">
            <div className="flex-1 bg-red-500" />
            <div className="flex-1 bg-orange-400" />
            <div className="flex-1 bg-yellow-400" />
            <div className="flex-1 bg-green-400" />
            <div className="flex-1 bg-green-500" />
          </div>
          <span>100%</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {sections.map((cell, idx) => {
          const pct = Math.round(cell.similarity * 100);
          const tooltipId = `${id}-tip-${idx}`;

          return (
            <button
              key={idx}
              aria-label={`${cell.title}: ${pct}% similar`}
              title={`${cell.title}\n${pct}% similarity`}
              onClick={() => onCellClick?.(cell.title)}
              className={`
                relative group rounded px-2 py-1.5 text-xs font-medium truncate max-w-[140px]
                transition-transform hover:scale-105 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
                ${similarityColor(cell.similarity)} ${textOnColor(cell.similarity)}
              `}
              data-testid={`heatmap-cell-${idx}`}
            >
              <span className="block truncate">{cell.title}</span>
              <span className="block text-[10px] opacity-80">{pct}%</span>

              {/* Tooltip */}
              <span
                id={tooltipId}
                role="tooltip"
                className="
                  pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5
                  hidden group-hover:block
                  bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10 shadow-lg
                "
              >
                {cell.title}: {pct}% similarity
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SectionHeatmap;
