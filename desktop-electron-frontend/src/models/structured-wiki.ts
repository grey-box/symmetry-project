// TypeScript interfaces matching the Python Pydantic models

export interface Citation {
  label: string;
  url?: string;
}

export interface Reference {
  label: string;
  id?: string;
  url?: string;
}

export interface Section {
  title: string;
  raw_content: string;
  clean_content: string;
  citations?: Citation[];
  citation_position?: string[];
}

export interface StructuredArticleResponse {
  title: string;
  lang: string;
  source: string;
  sections: Section[];
  references: Reference[];
  total_sections: number;
  total_citations: number;
  total_references: number;
}

export interface StructuredSectionResponse {
  title: string;
  raw_content: string;
  clean_content: string;
  citations?: Citation[];
  citation_position?: string[];
  word_count: number;
  citation_count: number;
}

export interface StructuredCitationResponse {
  citations: Citation[];
  total_citations: number;
  unique_targets: number;
  most_cited_articles: Array<{
    title: string;
    count: number;
  }>;
}

export interface StructuredReferenceResponse {
  references: Reference[];
  total_references: number;
  references_with_urls: number;
  reference_density: number;
}

// Request interfaces
export interface StructuredArticleRequest {
  query: string;
  lang?: string;
}

export interface StructuredSectionRequest {
  query: string;
  lang?: string;
  section_title: string;
}

export interface CitationAnalysisRequest {
  query: string;
  lang?: string;
}

export interface ReferenceAnalysisRequest {
  query: string;
  lang?: string;
}
