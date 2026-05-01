import {
  StructuredArticleResponse,
  StructuredSectionResponse,
  StructuredCitationResponse,
  StructuredReferenceResponse,
  StructuredArticleRequest,
  StructuredSectionRequest,
  CitationAnalysisRequest,
  ReferenceAnalysisRequest,
  SectionCompareRequest,
  SectionCompareResponse,
  Revision,
  RevisionDiffResponse,
  RevisionDetailedDiffResponse,
  Section,
  ParagraphDiffRequest,
  ParagraphDiffResponse,
} from '../models/structured-wiki';
import { FactExtractionModel, FactExtractionRequest, FactExtractionResponse } from '../models/FactExtraction';

// Get API base URL from constants
const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * Service for interacting with structured Wikipedia API endpoints
 */
class StructuredWikiService {

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetchWithErrorHandling<T>(url: string): Promise<T> {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Fetch error:', error);
      throw error;
    }
  }

  /**
   * Get a structured Wikipedia article with rich metadata
   */
  async getStructuredArticle(request: StructuredArticleRequest): Promise<StructuredArticleResponse> {
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.lang) {
      params.append('lang', request.lang);
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/structured-article?${params.toString()}`;
    return this.fetchWithErrorHandling<StructuredArticleResponse>(url);
  }

  /**
   * Get a translated version of a structured article
   */
  async getTranslatedStructuredArticle(params: {
    source_lang: string;
    target_lang: string;
    title?: string;
    url?: string;
  }): Promise<StructuredArticleResponse> {
    const searchParams = new URLSearchParams();

    searchParams.append('source_lang', params.source_lang);
    searchParams.append('target_lang', params.target_lang);

    if (params.title) {
      searchParams.append('title', params.title);
    }
    if (params.url) {
      searchParams.append('url', params.url);
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/structured-translated-article?${searchParams.toString()}`;
    return this.fetchWithErrorHandling<StructuredArticleResponse>(url);
  }


  /**
   * Get a specific section from a structured article
   */
  async getStructuredSection(request: StructuredSectionRequest): Promise<StructuredSectionResponse> {
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.lang) {
      params.append('lang', request.lang);
    }
    params.append('section_title', request.section_title);

    const url = `${API_BASE_URL}/symmetry/v1/wiki/structured-section?${params.toString()}`;
    return this.fetchWithErrorHandling<StructuredSectionResponse>(url);
  }

  /**
   * Get detailed citation analysis for an article
   */
  async getCitationAnalysis(request: CitationAnalysisRequest): Promise<StructuredCitationResponse> {
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.lang) {
      params.append('lang', request.lang);
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/citation-analysis?${params.toString()}`;
    return this.fetchWithErrorHandling<StructuredCitationResponse>(url);
  }

  /**
   * Get detailed reference analysis for an article
   */
  async getReferenceAnalysis(request: ReferenceAnalysisRequest): Promise<StructuredReferenceResponse> {
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.lang) {
      params.append('lang', request.lang);
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/reference-analysis?${params.toString()}`;
    return this.fetchWithErrorHandling<StructuredReferenceResponse>(url);
  }

  /**
   * Compare two Wikipedia articles section-by-section using semantic + Levenshtein analysis.
   * Returns paragraph-level diffs for each matched/missing/added section.
   */
  async compareSections(request: SectionCompareRequest): Promise<SectionCompareResponse> {
    const response = await fetch(`${API_BASE_URL}/symmetry/v1/articles/compare-sections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Section comparison failed (${response.status}): ${errorBody}`);
    }

    return response.json();
  }

  /**
   * Get revision history for a Wikipedia article.
   */
  async getRevisionHistory(request: { query: string; lang?: string; limit?: number }): Promise<Revision[]> {
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.lang) {
      params.append('lang', request.lang);
    }
    if (request.limit !== undefined) {
      params.append('limit', String(request.limit));
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/revision-history?${params.toString()}`;
    return this.fetchWithErrorHandling<Revision[]>(url);
  }

  /**
   * Compare two revisions of the same article.
   */
  async getRevisionDiff(request: {
    revid_a: number;
    revid_b: number;
    title: string;
    lang?: string;
  }): Promise<RevisionDiffResponse> {
    const params = new URLSearchParams();
    params.append('revid_a', String(request.revid_a));
    params.append('revid_b', String(request.revid_b));
    params.append('title', request.title);
    if (request.lang) {
      params.append('lang', request.lang);
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/diff?${params.toString()}`;
    return this.fetchWithErrorHandling<RevisionDiffResponse>(url);
  }

  /**
   * Compare two revisions and return detailed section diffs, with optional flagging.
   */
  async getRevisionDetailedDiff(request: {
    old_revid: number;
    new_revid: number;
    title: string;
    lang?: string;
    include_flags?: boolean;
  }): Promise<RevisionDetailedDiffResponse> {
    const params = new URLSearchParams();
    params.append('old_revid', String(request.old_revid));
    params.append('new_revid', String(request.new_revid));
    params.append('title', request.title);
    if (request.lang) {
      params.append('lang', request.lang);
    }
    if (request.include_flags !== undefined) {
      params.append('include_flags', String(request.include_flags));
    }

    const url = `${API_BASE_URL}/symmetry/v1/wiki/revision-diff?${params.toString()}`;
    return this.fetchWithErrorHandling<RevisionDetailedDiffResponse>(url);
  }

  /**
   * Utility method to parse Wikipedia URL and extract title and language
   */
  parseWikipediaUrl(url: string): { title: string; lang: string } | null {
    try {
      const urlPattern = /https?:\/\/([a-z]{2})\.wikipedia\.org\/wiki\/(.+)/;
      const match = url.match(urlPattern);

      if (match) {
        return {
          lang: match[1] ?? 'en',
          title: decodeURIComponent((match[2] ?? '').replace(/_/g, ' '))
        };
      }

      return null;
    } catch (error) {
      console.error('Error parsing Wikipedia URL:', error);
      return null;
    }
  }

  /**
   * Convenience method to get structured article from URL
   */
  async getStructuredArticleFromUrl(url: string): Promise<StructuredArticleResponse> {
    const parsed = this.parseWikipediaUrl(url);
    if (!parsed) {
      throw new Error('Invalid Wikipedia URL format');
    }

    return this.getStructuredArticle({
      query: parsed.title,
      lang: parsed.lang
    });
  }

  /**
   * Convenience method to get structured article from title
   */
  async getStructuredArticleFromTitle(title: string, lang: string = 'en'): Promise<StructuredArticleResponse> {
    return this.getStructuredArticle({
      query: title,
      lang
    });
  }

  /**
   * Get article statistics summary
   */
  getArticleStats(article: StructuredArticleResponse) {
    const totalWords = article.sections.reduce((sum, s) => sum + s.clean_content.split(' ').length, 0);

    return {
      title: article.title,
      language: article.lang,
      totalSections: article.total_sections,
      totalCitations: article.total_citations,
      totalReferences: article.total_references,
      totalWords,
      averageCitationsPerSection: article.total_sections > 0 ?
        (article.total_citations / article.total_sections).toFixed(1) : '0',
      referenceDensity: totalWords > 0 ?
        (article.total_references / totalWords * 1000).toFixed(2) : '0'
    };
  }

  /**
   * Search for sections by title substring
   */
  searchSections(article: StructuredArticleResponse, searchTerm: string): Section[] {
    if (!searchTerm.trim()) {
      return article.sections;
    }

    const term = searchTerm.toLowerCase();
    return article.sections.filter(section =>
      section.title.toLowerCase().includes(term) ||
      section.clean_content.toLowerCase().includes(term)
    );
  }

  /**
   * Get most cited articles from citation analysis
   */
  getMostCitedArticles(citationAnalysis: StructuredCitationResponse, limit: number = 5) {
    return citationAnalysis.most_cited_articles
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }

  /**
   * Format section content for display
   */
  formatSectionContent(section: Section): string {
    return section.clean_content;
  }

  /**
   * Get citation positions as a readable string
   */
  formatCitationPositions(positions: string[]): string {
    if (!positions || positions.length === 0) {
      return 'No citations found';
    }
    return positions.slice(0, 5).join(', ') + (positions.length > 5 ? '...' : '');
  }

  /**
   * Get available fact extraction models
   */
  async getFactExtractionModels(): Promise<FactExtractionModel[]> {
    const url = `${API_BASE_URL}/symmetry/v1/wiki/fact-extraction-models`;
    return this.fetchWithErrorHandling<FactExtractionModel[]>(url);
  }

  /**
   * Extract facts from a section's content using a specific model
   */
  async extractFacts(request: FactExtractionRequest): Promise<FactExtractionResponse> {
    const url = `${API_BASE_URL}/symmetry/v1/wiki/extract-facts`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Validate a custom fact extraction model
   */
  async validateFactExtractionModel(modelId: string): Promise<{ valid: boolean; model?: FactExtractionModel; error?: string }> {
    const url = `${API_BASE_URL}/symmetry/v1/wiki/fact-extraction-validate?model_id=${encodeURIComponent(modelId)}`;
    return this.fetchWithErrorHandling<{ valid: boolean; model?: FactExtractionModel; error?: string }>(url);
  }

  /**
   * Parse a Wikipedia URL, detect source language and title, and return available
   * target languages with their translated article titles.
   */
  async getArticleLanguages(url: string): Promise<{
    source_lang: string;
    source_title: string;
    available_targets: Array<{ lang: string; title: string }>;
  }> {
    const params = new URLSearchParams({ url });
    return this.fetchWithErrorHandling(
      `${API_BASE_URL}/symmetry/v1/wiki/article-languages?${params.toString()}`
    );
  }

  /**
   * Get paragraph-level semantic diff between two Wikipedia articles.
   * Returns sentence-aligned pairs with word-level token diffs (equal/replace/insert/delete).
   */
  async getParagraphDiff(request: ParagraphDiffRequest): Promise<ParagraphDiffResponse> {
    const response = await fetch(`${API_BASE_URL}/symmetry/v1/wiki/paragraph-diff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Paragraph diff failed (${response.status}): ${errorBody}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const structuredWikiService = new StructuredWikiService();
export default structuredWikiService;
