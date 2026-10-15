const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const defaultApiBaseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';

export const API_BASE_URL = normalizeApiBaseUrl(
  configuredApiBaseUrl || defaultApiBaseUrl,
);
const API_PREFIX = API_BASE_URL ? `${API_BASE_URL}/api/v1` : '';

function normalizeApiBaseUrl(value: string): string {
  return value
    .replace(/\/+$/, '')
    .replace(/(?:\/api\/v1)+$/i, '');
}

export function apiUrl(path: string): string {
  if (!API_BASE_URL) {
    throw new Error('VITE_API_BASE_URL must be set for production builds.');
  }

  const endpoint = path
    .trim()
    .replace(/^(?:\/?api\/v1)+(?=\/|$)/i, '')
    .replace(/^\/+/, '');
  return endpoint ? `${API_PREFIX}/${endpoint}` : API_PREFIX;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function apiRequest<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(apiUrl(path), { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as {
      error?: { code?: string; message?: string };
    } | null;
    throw new ApiError(
      response.status,
      payload?.error?.code ?? 'request_failed',
      payload?.error?.message ?? `Request failed (${response.status})`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface ApiUser {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface ApiWorkspace {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  plan: 'starter' | 'pro' | 'enterprise';
  is_active: boolean;
  created_at: string;
  role: 'admin' | 'support_agent' | 'user';
}

export interface ApiDocument {
  id: number;
  workspace_id: number;
  uploaded_by_id: number;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  sha256: string;
  embedding_model: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  page_count: number | null;
  chunk_count: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiDocumentChunk {
  id: number;
  chunk_index: number;
  page_number: number | null;
  content: string;
}

export interface ApiDocumentDetail extends ApiDocument {
  chunks: ApiDocumentChunk[];
}

export interface ApiConversation {
  id: number;
  workspace_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: Array<{
    source_id: string;
    document_id: number;
    document_name: string;
    page_number: number | null;
    chunk_index: number;
    excerpt: string;
    relevance_score: number;
  }>;
  created_at: string;
}

export interface ApiMember {
  user_id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'support_agent' | 'user';
  is_active: boolean;
  joined_at: string;
}

export interface WorkspaceAnalytics {
  document_count: number;
  documents_by_status: Record<string, number>;
  conversation_count: number;
  active_member_count: number;
}

export function workspacePath(workspaceId: number, suffix = ''): string {
  return `/workspaces/${workspaceId}${suffix}`;
}
