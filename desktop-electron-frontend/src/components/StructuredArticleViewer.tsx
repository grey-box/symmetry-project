import React, { useState, useEffect, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import {
  StructuredArticleResponse,
  StructuredCitationResponse,
  StructuredReferenceResponse,
  SectionCompareResponse,
  Section
} from '../models/structured-wiki';
import { structuredWikiService } from '../services/structuredWikiService';
import { FactExtractionModel, FactExtractionResponse } from '../models/FactExtraction';

const languageCodes = [
  'en', 'es', 'fr', 'de', 'it', 'pt',
  'nl', 'pl', 'ru', 'zh', 'ja',
  'ko', 'ar', 'hi', 'tr',
];

const displayNames = new Intl.DisplayNames(['en'], { type: 'language' });
const TRANSLATION_LANGUAGES = languageCodes.map(code => ({
  code,
  label: displayNames.of(code) ?? code,
}));



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
  const [targetLang, setTargetLang] = useState(initialLang);
  const [translating, setTranslating] = useState(false);

  // Fact extraction states
  const [factModels, setFactModels] = useState<FactExtractionModel[]>([]);
  const [selectedFactModel, setSelectedFactModel] = useState<string>('');
  const [customFactModel, setCustomFactModel] = useState<string>('');
  const [customModelValidation, setCustomModelValidation] = useState<{ valid: boolean; error?: string } | null>(null);
  const [validatingCustomModel, setValidatingCustomModel] = useState<boolean>(false);
  const [sectionFacts, setSectionFacts] = useState<Record<string, FactExtractionResponse>>({});
  const [extractingSection, setExtractingSection] = useState<string | null>(null);
  const [factError, setFactError] = useState<string | null>(null);
  const [numFacts, setNumFacts] = useState<number>(1);
  const [autoNumFacts, setAutoNumFacts] = useState<boolean>(false);
  const [hoveredChunk, setHoveredChunk] = useState<string | null>(null);
  const [clickedChunk, setClickedChunk] = useState<string | null>(null);

  // Section comparison state
  const [comparisonResult, setComparisonResult] = useState<SectionCompareResponse | null>(null);
  const [compareLang, setCompareLang] = useState('es');
  const [comparing, setComparing] = useState(false);
  const [showComparison, setShowComparison] = useState(false);



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

  const translateArticle = async () => {
    if (!article) return;

    setTranslating(true);
    setError(null);

    try {
      const translatedArticle =
        await structuredWikiService.getTranslatedStructuredArticle({
          source_lang: article.lang,
          target_lang: targetLang,
          title: article.title,
        });

      setArticle(translatedArticle);
      setTargetLang(translatedArticle.lang);
      setCitationAnalysis(null); // These are temporarily set to NULL, as we only want content translated.
      setReferenceAnalysis(null); // In the future, we may use this to compare citations/references between languages.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to translate article');
    } finally {
      setTranslating(false);
    }
  };


  /** Run section-by-section comparison against another language */
  const runSectionComparison = async () => {
    if (!article) return;

    setComparing(true);
    setError(null);

    try {
      const result = await structuredWikiService.compareSections({
        source_query: article.title,
        target_query: article.title, // same article, different language
        source_lang: article.lang,
        similarity_threshold: 0.5,
      });

      setComparisonResult(result);
      setShowComparison(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Section comparison failed');
    } finally {
      setComparing(false);
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

  useEffect(() => {
    if (!article) return;

    if (
      !selectedSection ||
      !article.sections.some(s => s.title === selectedSection)
    ) {
      setSelectedSection(article.sections[0]?.title ?? null);
    }
  }, [article, selectedSection]);

  // Auto-calculate num_facts based on selected section word count
  useEffect(() => {
    if (!autoNumFacts || !article || !selectedSection) return;

    const section = article.sections.find(s => s.title === selectedSection);
    if (section) {
      const wordCount = section.clean_content.split(' ').length;
      // Calculate: roughly 1 fact per 50 words, minimum 1, maximum 20
      const calculated = Math.max(1, Math.min(20, Math.ceil(wordCount / 50)));
      setNumFacts(calculated);
    }
  }, [autoNumFacts, selectedSection, article]);

  // Load available fact extraction models on mount
  useEffect(() => {
    const loadFactModels = async () => {
      try {
        const models = await structuredWikiService.getFactExtractionModels();
        setFactModels(models);
        if (models.length > 0 && !selectedFactModel) {
          setSelectedFactModel(models[0].id);
        }
      } catch (err) {
        console.error('Failed to load fact extraction models:', err);
        setFactError('Failed to load fact extraction models');
      }
    };

    loadFactModels();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      loadArticle(searchInput.trim(), initialLang);
    }
  };

  const handleExtractFacts = async (sectionTitle: string, content: string) => {
    if (!selectedFactModel) {
      setFactError('Please select a fact extraction model');
      return;
    }

    setExtractingSection(sectionTitle);
    setFactError(null);

    try {
      const response = await structuredWikiService.extractFacts({
        section_content: content,
        model_id: selectedFactModel,
        section_title: sectionTitle,
        num_facts: numFacts
      });

      setSectionFacts(prev => ({
        ...prev,
        [sectionTitle]: response
      }));
    } catch (err) {
      console.error('Error extracting facts:', err);
      setFactError(err instanceof Error ? err.message : 'Failed to extract facts');
    } finally {
      setExtractingSection(null);
    }
  };

  const handleValidateCustomModel = async () => {
    if (!customFactModel.trim()) {
      setCustomModelValidation({ valid: false, error: 'Please enter a model name' });
      return;
    }

    setValidatingCustomModel(true);
    setCustomModelValidation(null);
    setFactError(null);

    try {
      const result = await structuredWikiService.validateFactExtractionModel(customFactModel.trim());
      setCustomModelValidation(result);

      if (result.valid && result.model) {
        // Auto-select the custom model
        setSelectedFactModel(result.model.id);
      }
    } catch (err) {
      console.error('Error validating custom model:', err);
      setCustomModelValidation({
        valid: false,
        error: err instanceof Error ? err.message : 'Validation failed'
      });
    } finally {
      setValidatingCustomModel(false);
    }
  };

  // Helper to highlight hovered/clicked chunk in content
  const highlightChunk = (content: string, chunk: string | null, isClickHighlight = false): React.ReactNode => {
    if (!chunk) return content;

    // Escape regex special characters in the chunk
    const escapedChunk = chunk.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // Split content by the chunk (case-insensitive)
    const parts = content.split(new RegExp(`(${escapedChunk})`, 'gi'));

    if (parts.length === 1) return content; // Chunk not found

    return (
      <>
        {parts.map((part, index) => {
          // Check if this part matches the chunk (case-insensitive)
          if (part.toLowerCase() === chunk.toLowerCase()) {
            return (
              <mark
                key={index}
                className={`${isClickHighlight ? 'bg-orange-200 outline outline-2 outline-orange-400' : 'bg-yellow-200 outline outline-1 outline-yellow-400'} px-0.5 rounded`}
              >
                {part}
              </mark>
            );
          }
          return part;
        })}
      </>
    );
  };

  // Handle fact click - scroll to chunk in passage
  const handleFactClick = (chunk: string) => {
    // Toggle off if already clicked
    if (clickedChunk === chunk) {
      setClickedChunk(null);
    } else {
      setClickedChunk(chunk);
      // Scroll to the highlighted chunk after re-render
      setTimeout(() => {
        // Find the first mark element with the clicked chunk
        const marks = document.querySelectorAll('mark');
        for (const mark of marks) {
          if (mark.textContent?.toLowerCase() === chunk.toLowerCase()) {
            mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
            break;
          }
        }
      }, 50);
    }
  };

  // Clear clicked highlight when section changes
  useEffect(() => {
    return () => {
      setClickedChunk(null);
      setHoveredChunk(null);
    };
  }, [selectedSection]);

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

        {/* Translate Button Row */}
        {article && (
          <div className="mb-6 flex flex-wrap items-center gap-4">
            {/* Translation Controls */}
            <div className="flex items-center gap-4">
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
                disabled={translating}
              >
                {TRANSLATION_LANGUAGES.map(lang => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>

              <button
                onClick={translateArticle}
                disabled={translating || targetLang === article.lang}
                className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {translating ? 'Translating...' : 'Translate'}
              </button>

              <span className="text-sm text-gray-500">
                {article.lang} → {targetLang}
              </span>
            </div>
          </div>
        )}

        {/* Fact Extraction Model Selection & Options - with Extract Facts button */}
        {article && (
          <div className="mb-6 flex flex-wrap items-center gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Model:</span>
                <select
                  value={selectedFactModel}
                  onChange={(e) => setSelectedFactModel(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={factModels.length === 0}
                >
                  {factModels.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Custom Model Input */}
              <div className="flex items-center gap-2">
                <div className="flex-1 max-w-md">
                  <input
                    type="text"
                    value={customFactModel}
                    onChange={(e) => setCustomFactModel(e.target.value)}
                    placeholder="Or paste HuggingFace model name (e.g., google/flan-t5-large)"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleValidateCustomModel();
                      }
                    }}
                  />
                </div>
                <button
                  onClick={handleValidateCustomModel}
                  disabled={validatingCustomModel || !customFactModel.trim()}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {validatingCustomModel ? 'Validating...' : 'Validate & Use'}
                </button>
              </div>

              {/* Custom Model Validation Feedback */}
              {customModelValidation && (
                <div className={`text-sm ${customModelValidation.valid ? 'text-green-600' : 'text-red-600'}`}>
                  {customModelValidation.valid ? (
                    <span>✓ Model validated and selected: {selectedFactModel}</span>
                  ) : (
                    <span>✗ {customModelValidation.error || 'Validation failed'}</span>
                  )}
                </div>
              )}
            </div>

            {/* Number of Facts Control */}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={autoNumFacts}
                  onChange={(e) => setAutoNumFacts(e.target.checked)}
                  className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                />
                Auto
              </label>

              {!autoNumFacts && (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={numFacts}
                    onChange={(e) => setNumFacts(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    title="Number of facts to extract"
                  />
                  <span className="text-sm text-gray-500">facts</span>
                </div>
              )}

              {autoNumFacts && (
                <span className="text-sm text-gray-500">
                  (auto: based on section length)
                </span>
              )}
            </div>

            {/* Extract Facts Button - inside the model selection box */}
            <div className="flex items-center gap-2 ml-4 border-l border-gray-300 pl-4">
              <button
                onClick={() => {
                  if (selectedSection) {
                    const section = filteredSections.find(s => s.title === selectedSection);
                    if (section) {
                      handleExtractFacts(section.title, section.clean_content);
                    }
                  }
                }}
                disabled={extractingSection !== null || !selectedFactModel || !selectedSection}
                className="px-6 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {extractingSection ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Extracting...
                  </>
                ) : (
                  'Extract Facts'
                )}
              </button>

              {/* Show which section is being extracted */}
              {extractingSection && (
                <span className="text-sm text-gray-500">
                  from "{extractingSection}"
                </span>
              )}
            </div>
          </div>
        )}



        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Fact Extraction Error Display */}
        {factError && (
          <div className="mb-6 p-4 bg-orange-100 border border-orange-400 text-orange-700 rounded">
            {factError}
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
        {!showComparison && mostCited.length > 0 && (
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
        {!showComparison && article && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Section Navigation */}
            <div className="lg:col-span-1">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Sections</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredSections.map((section, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedSection(section.title)}
                    className={`w-full text-left p-2 rounded transition-colors ${selectedSection === section.title
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
            <div className="lg:col-span-3" id="section-content-area">
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
                            {clickedChunk && sectionFacts[section.title]?.chunks
                              ? highlightChunk(section.clean_content, clickedChunk, true)
                              : (hoveredChunk && sectionFacts[section.title]?.chunks
                                ? highlightChunk(section.clean_content, hoveredChunk)
                                : structuredWikiService.formatSectionContent(section))}
                          </p>
                        </div>

                        {/* Extracted Facts - between passage and citations */}
                        {sectionFacts[section.title] && (
                          <div className="mt-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                            <div className="flex items-center gap-2 mb-3">
                              <h5 className="font-semibold text-purple-900">
                                Extracted Facts
                              </h5>
                              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                                {sectionFacts[section.title].model_used}
                              </span>
                            </div>
                            {sectionFacts[section.title].facts.length > 0 ? (
                              <ul className="space-y-2">
                                {sectionFacts[section.title].facts.map((fact, index) => {
                                  const chunk = sectionFacts[section.title]?.chunks?.[index] || '';
                                  const isHovered = hoveredChunk === chunk;
                                  const isClicked = clickedChunk === chunk;
                                  return (
                                    <li
                                      key={index}
                                      className={`flex items-start gap-2 text-sm text-gray-700 p-2 rounded transition-colors cursor-pointer ${isClicked ? 'bg-orange-100 outline outline-2 outline-orange-400' : isHovered ? 'bg-yellow-100' : ''
                                        }`}
                                      onMouseEnter={() => setHoveredChunk(chunk)}
                                      onMouseLeave={() => setHoveredChunk(null)}
                                      onClick={() => handleFactClick(chunk)}
                                    >
                                      <span className="text-purple-500 mt-1">•</span>
                                      <span>{fact}</span>
                                    </li>
                                  );
                                })}
                              </ul>
                            ) : (
                              <p className="text-sm text-gray-600 italic">
                                No facts could be extracted from this section.
                              </p>
                            )}
                          </div>
                        )}

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

                        {/* Extract Facts Button */}
                        <div className="mt-6">
                          <button
                            onClick={() => handleExtractFacts(section.title, section.clean_content)}
                            disabled={extractingSection === section.title || !selectedFactModel}
                            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                          >
                            {extractingSection === section.title ? (
                              <>
                                <Loader2 size={16} className="animate-spin" />
                                Extracting...
                              </>
                            ) : (
                              'Extract Facts'
                            )}
                          </button>
                        </div>

                        {/* Display Extracted Facts */}
                        {sectionFacts[section.title] && (
                          <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                            <div className="flex items-center gap-2 mb-3">
                              <h5 className="font-semibold text-purple-900">
                                Extracted Facts
                              </h5>
                              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                                {sectionFacts[section.title].model_used}
                              </span>
                            </div>
                            {sectionFacts[section.title].facts.length > 0 ? (
                              <ul className="space-y-2">
                                {sectionFacts[section.title].facts.map((fact, index) => (
                                  <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                                    <span className="text-purple-500 mt-1">•</span>
                                    <span>{fact}</span>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-sm text-gray-600 italic">
                                No facts could be extracted from this section.
                              </p>
                            )}
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
        {!showComparison && referenceAnalysis && referenceAnalysis.references.length > 0 && (
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