// Request and response models for fact extraction API

export interface FactExtractionModel {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  description: string;
}

export interface FactExtractionValidationResponse {
  valid: boolean;
  model?: FactExtractionModel;
  error?: string;
}

export interface FactExtractionRequest {
  section_content: string;
  model_id: string;
  section_title?: string;
  num_facts?: number;
}

export interface FactExtractionResponse {
  facts: string[];
  model_used: string;
  section_title: string;
  chunks: string[];
}
