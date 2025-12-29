import {
  StructuredArticleResponse,
  StructuredSectionResponse,
  StructuredCitationResponse,
  StructuredReferenceResponse,
  StructuredArticleRequest,
  StructuredSectionRequest,
  CitationAnalysisRequest,
  ReferenceAnalysisRequest,
  Section
} from '../models/structured-wiki';

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
   * Utility method to parse Wikipedia URL and extract title and language
   */
  parseWikipediaUrl(url: string): { title: string; lang: string } | null {
    try {
      const urlPattern = /https?:\/\/([a-z]{2})\.wikipedia\.org\/wiki\/(.+)/;
      const match = url.match(urlPattern);
      
      if (match) {
        return {
          lang: match[1],
          title: decodeURIComponent(match[2].replace(/_/g, ' '))
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
  formatSectionContent(section: Section, maxLength: number = 500): string {
    if (section.clean_content.length <= maxLength) {
      return section.clean_content;
    }
    return section.clean_content.substring(0, maxLength) + '...';
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
}

// Export singleton instance
export const structuredWikiService = new StructuredWikiService();
export default structuredWikiService;
