import React, { useState, useEffect } from 'react';
import {
  StructuredArticleResponse,
  StructuredCitationResponse,
  StructuredReferenceResponse,
  Section
} from '../models/structured-wiki';
import { structuredWikiService } from '../services/structuredWikiService';

interface StructuredArticleViewerProps {
  initialQuery?: string;
  initialLang?: string;
}

const StructuredArticleViewer: React.FC<StructuredArticleViewerProps> = ({
  initialQuery = '',
  initialLang = 'en'
}) => {
  const [article, setArticle] = useState<StructuredArticleResponse | null>(null);
  const [citationAnalysis, setCitationAnalysis] = useState<StructuredCitationResponse | null>(null);
  const [referenceAnalysis, setReferenceAnalysis] = useState<StructuredReferenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState(''); // For section search
  const [searchInput, setSearchInput] = useState(''); // For article search input
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  // Load article data
  const loadArticle = async (query: string, lang: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const [articleData, citationsData, referencesData] = await Promise.all([
        structuredWikiService.getStructuredArticle({ query, lang }),
        structuredWikiService.getCitationAnalysis({ query, lang }),
        structuredWikiService.getReferenceAnalysis({ query, lang })
      ]);
      
      setArticle(articleData);
      setCitationAnalysis(citationsData);
      setReferenceAnalysis(referencesData);
      
      if (articleData.sections.length > 0) {
        setSelectedSection(articleData.sections[0].title);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load article');
    } finally {
      setLoading(false);
    }
  };

  // Search sections (for section navigation)
  const filteredSections = article ? structuredWikiService.searchSections(article, searchTerm) : [];

  // Get article stats
  const articleStats = article ? structuredWikiService.getArticleStats(article) : null;

  // Most cited articles
  const mostCited = citationAnalysis ? structuredWikiService.getMostCitedArticles(citationAnalysis) : [];

  useEffect(() => {
    if (initialQuery) {
      setSearchInput(initialQuery); // Set initial query as the starting search input
      loadArticle(initialQuery, initialLang);
    }
  }, [initialQuery, initialLang]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      loadArticle(searchInput.trim(), initialLang);
    }
  };

  return (
    <div className="structured-article-viewer p-6 max-w-7xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Structured Wikipedia Article Viewer</h1>
        
        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="flex gap-4">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Enter Wikipedia article title or URL"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !searchInput.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Load Article'}
            </button>
          </div>
        </form>

        {/* Section Search */}
        {article && (
          <div className="mb-4">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search within sections..."
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Article Statistics */}
        {articleStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-blue-600">Sections</h3>
              <p className="text-2xl font-bold text-blue-800">{articleStats.totalSections}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-green-600">Citations</h3>
              <p className="text-2xl font-bold text-green-800">{articleStats.totalCitations}</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-purple-600">References</h3>
              <p className="text-2xl font-bold text-purple-800">{articleStats.totalReferences}</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-orange-600">Words</h3>
              <p className="text-2xl font-bold text-orange-800">{articleStats.totalWords?.toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Most Cited Articles */}
        {mostCited.length > 0 && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Most Cited Articles</h3>
            <div className="space-y-2">
              {mostCited.map((item, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-gray-700">{item.title}</span>
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    {item.count} citations
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Article Content */}
        {article && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Section Navigation */}
            <div className="lg:col-span-1">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Sections</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredSections.map((section, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedSection(section.title)}
                    className={`w-full text-left p-2 rounded transition-colors ${
                      selectedSection === section.title
                        ? 'bg-blue-100 text-blue-800 border-l-4 border-blue-500'
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="font-medium">{section.title}</div>
                    <div className="text-sm text-gray-500">
                      {section.citations?.length || 0} citations
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Section Content */}
            <div className="lg:col-span-3">
              {selectedSection && (
                <div>
                  {(() => {
                    const section = filteredSections.find(s => s.title === selectedSection);
                    if (!section) return null;

                    return (
                      <div className="space-y-4">
                        <div className="border-b border-gray-200 pb-4">
                          <h2 className="text-2xl font-bold text-gray-800">{section.title}</h2>
                          <div className="text-sm text-gray-500 mt-1">
                            {section.clean_content.split(' ').length} words
                            {section.citations && section.citations.length > 0 && (
                              <span> • {section.citations.length} citations</span>
                            )}
                          </div>
                        </div>

                        {/* Section Content */}
                        <div className="prose prose-blue max-w-none">
                          <p className="text-gray-700 leading-relaxed">
                            {structuredWikiService.formatSectionContent(section)}
                          </p>
                        </div>

                        {/* Citations */}
                        {section.citations && section.citations.length > 0 && (
                          <div className="mt-6">
                            <h4 className="text-lg font-semibold text-gray-800 mb-3">Citations</h4>
                            <div className="space-y-2">
                              {section.citations.map((citation, index) => (
                                <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium min-w-fit">
                                    [{index + 1}]
                                  </span>
                                  <div className="flex-1">
                                    <div className="font-medium text-gray-800">{citation.label}</div>
                                    {citation.url && (
                                      <a
                                        href={citation.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800 text-sm"
                                      >
                                        View on Wikipedia
                                      </a>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Citation Positions */}
                        {section.citation_position && section.citation_position.length > 0 && (
                          <div className="mt-4 p-3 bg-yellow-50 rounded">
                            <h5 className="font-medium text-yellow-800 mb-2">Citation Positions</h5>
                            <p className="text-sm text-yellow-700">
                              {structuredWikiService.formatCitationPositions(section.citation_position)}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          </div>
        )}

        {/* References Section */}
        {referenceAnalysis && referenceAnalysis.references.length > 0 && (
          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-xl font-bold text-gray-800 mb-4">
              References ({referenceAnalysis.total_references})
            </h3>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {referenceAnalysis.references.slice(0, 10).map((reference, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded border-l-4 border-gray-300">
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">[{index + 1}]</span>
                    {reference.id && (
                      <span className="ml-2 text-xs bg-gray-200 px-2 py-1 rounded">
                        {reference.id}
                      </span>
                    )}
                  </div>
                  <div className="text-gray-800 text-sm">
                    {reference.label.length > 200 
                      ? reference.label.substring(0, 200) + '...' 
                      : reference.label
                    }
                  </div>
                  {reference.url && (
                    <a
                      href={reference.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 text-sm mt-1 inline-block"
                    >
                      Source
                    </a>
                  )}
                </div>
              ))}
            </div>
            {referenceAnalysis.references.length > 10 && (
              <div className="text-center mt-4">
                <span className="text-gray-500 text-sm">
                  Showing 10 of {referenceAnalysis.references.length} references
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StructuredArticleViewer;
