// User & Auth Types
export enum UserRole {
  SUPER_ADMIN = "super_admin",
  TENANT_ADMIN = "tenant_admin",
  USER = "user",
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  tenant_id?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

// Tenant Types
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// Document Types
export enum DocumentStatus {
  UPLOADING = "uploading",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  DELETED = "deleted",
}

export interface Document {
  id: string;
  tenant_id: string;
  user_id: string | null;
  filename: string;
  file_path: string;
  file_size: number;
  file_type: string;
  status: DocumentStatus;
  content: string | null;
  chunk_count: number;
  error_message: string | null;
  doc_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  status: DocumentStatus;
  message: string;
}

export interface DocumentSearchRequest {
  query: string;
  limit?: number;
  score_threshold?: number;
  filter_metadata?: Record<string, unknown>;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  score: number;
  chunk_index: number;
  chunk_metadata: Record<string, unknown> | null;
  doc_metadata: Record<string, unknown> | null;
}

export interface DocumentSearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  tenant_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  chunk_metadata: Record<string, unknown> | null;
  start_char: number | null;
  end_char: number | null;
  created_at: string;
  updated_at: string;
}

// Embedding Provider Types
export enum ProviderType {
  OPENAI = "openai",
  OLLAMA = "ollama",
  CLAUDE = "claude",
  GEMINI = "gemini",
}

export interface EmbeddingProviderUpdate {
  provider: ProviderType;
  model: string;
  api_key?: string;
  base_url?: string;
}

export interface EmbeddingProviderResponse {
  provider: ProviderType;
  model: string;
  dimensions: number;
  base_url?: string;
  has_api_key: boolean;
}

export interface EmbeddingProviderTest {
  provider: ProviderType;
  model: string;
  api_key?: string;
  base_url?: string;
}

export interface EmbeddingProviderTestResponse {
  success: boolean;
  message: string;
  dimensions?: number;
}

// ====== LLM Provider Types ======

export interface LLMProviderUpdate {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
}

export interface LLMProviderResponse {
  provider: string;
  model: string;
  base_url?: string;
  has_api_key: boolean;
}

// ====== LLM Types ======

export interface DocumentSummarizeRequest {
  document_id: string;
  model?: string;
  max_length?: number;
}

export interface DocumentOperationStartResponse {
  operation_id: string;
  status: string;
  message: string;
}

export interface DocumentSummarizeResponse {
  operation_id: string;
  summary: string;
  model_used: string;
  tokens_used: number;
  cost_estimate: number;
}

export interface DocumentAskRequest {
  document_id: string;
  question: string;
  model?: string;
  include_chunks?: boolean;
  max_chunks?: number;
}

export interface DocumentAskResponse {
  operation_id: string;
  answer: string;
  sources: Array<{
    chunk_index: number;
    score: number;
    content_preview: string;
  }>;
  model_used: string;
  tokens_used: number;
  cost_estimate: number;
}

export interface DocumentTransformRequest {
  document_id: string;
  instruction: string;
  model?: string;
  output_format?: 'text' | 'markdown' | 'json';
}

export interface DocumentTransformResponse {
  operation_id: string;
  transformed_content: string;
  model_used: string;
  tokens_used: number;
  cost_estimate: number;
}

export interface LLMOperation {
  id: string;
  tenant_id: string;
  user_id: string;
  document_id: string | null;
  operation_type: 'summarize' | 'ask' | 'transform';
  input_data: any;
  output_data: any;
  model_used: string | null;
  tokens_used: number | null;
  cost_estimate: number | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
