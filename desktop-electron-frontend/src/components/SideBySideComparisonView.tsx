import React from 'react';
import { ParagraphDiffSection } from '../models/structured-wiki';
import SemanticWordDiff from './SemanticWordDiff';

interface SideBySideComparisonViewProps {
    sourceTitle: string;
    targetTitle: string;
    sourceLang?: string;
    targetLang?: string;
    sections: ParagraphDiffSection[];
}

/**
 * Single scrollable comparison view.
 * Renders section headers and SemanticWordDiff content in one aligned list.
 */
const SideBySideComparisonView: React.FC<SideBySideComparisonViewProps> = ({
    sourceTitle,
    targetTitle,
    sourceLang = 'en',
    targetLang = 'en',
    sections,
}) => {


    function similarityBadgeColor(sim: number) {
        if (sim >= 0.85) return 'bg-green-100 text-green-700';
        if (sim >= 0.6) return 'bg-yellow-100 text-yellow-700';
        return 'bg-red-100 text-red-700';
    }

    if (sections.length === 0) {
        return (
            <p className="text-sm text-gray-400 italic py-4 text-center">
                No sections available for side-by-side comparison.
            </p>
        );
    }

    // Build section blocks for the comparison list
    const sectionBlocks = sections.map((section, idx) => {
        const pct = Math.round(section.similarity * 100);
        const badgeClass = similarityBadgeColor(section.similarity);

        return (
            <div key={idx} className="border-b border-gray-100 last:border-0">
                {/* Shared sticky section header row */}
                <div className="sticky top-0 z-10 bg-gray-50 border-b border-gray-200 px-4 py-2 flex items-center gap-2">
                    <span className="font-semibold text-gray-800 text-sm flex-1">
                        {section.source_title}
                        {section.source_title !== section.target_title && (
                            <span className="ml-2 text-gray-400 font-normal text-xs">
                                → {section.target_title}
                            </span>
                        )}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badgeClass}`}>
                        {pct}% similar
                    </span>
                </div>

                {/* Pair content */}
                <div className="px-4 py-3">
                    <SemanticWordDiff
                        pairs={section.aligned_pairs}
                        sourceLang={sourceLang}
                        targetLang={targetLang}
                    />
                </div>
            </div>
        );
    });

    return (
        <div className="flex flex-col h-full" data-testid="side-by-side-comparison">
            {/* Column headers */}
            <div className="grid grid-cols-2 gap-4 px-4 py-2 bg-white border-b border-gray-200 sticky top-0 z-20">
                <div className="font-semibold text-gray-700 text-sm">
                    {sourceTitle}{' '}
                    <span className="text-xs text-gray-400 font-normal">({sourceLang})</span>
                </div>
                <div className="font-semibold text-gray-700 text-sm">
                    {targetTitle}{' '}
                    <span className="text-xs text-gray-400 font-normal">({targetLang})</span>
                </div>
            </div>

            {/* Scrollable content area — single shared list so headers align */}
            <div
                className="flex-1 overflow-y-auto"
                style={{ maxHeight: '70vh' }}
                data-testid="side-by-side-scroll-area"
            >
                {sectionBlocks}
            </div>
        </div>
    );
};

export default SideBySideComparisonView;
