// src/types/index.ts
// ─────────────────────
// Shared TypeScript types used across the entire frontend.

export type NavPage =
  | 'overview'
  | 'ai-chat'
  | 'documents'
  | 'conversations'
  | 'support-tickets'
  | 'team'
  | 'settings';

// ── Documents ─────────────────────────────────────────────────
export type DocumentFileType = 'pdf' | 'docx' | 'txt' | 'md' | 'csv';
export type DocumentStatus = 'processed' | 'processing' | 'failed';

export interface KnowledgeDocument {
  id: string;
  name: string;
  type: DocumentFileType;
  size: string;
  uploadedBy: string;
  uploadedAt: string;
  status: DocumentStatus;
  chunks: number;
  tags: string[];
}

// ── Support Tickets ────────────────────────────────────────────
export type TicketStatus = 'open' | 'in-progress' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export interface SupportTicket {
  id: string;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  assignee: string;
  reporter: string;
  createdAt: string;
  updatedAt: string;
  category: string;
  description: string;
}

// ── Team ───────────────────────────────────────────────────────
export type MemberRole = 'admin' | 'editor' | 'viewer';

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: MemberRole;
  department: string;
  joinedAt: string;
  lastActive: string;
  initials: string;
  avatarColor: string;
}

// ── Conversations ──────────────────────────────────────────────
export interface Conversation {
  id: string;
  title: string;
  preview: string;
  lastMessageAt: string;
  messageCount: number;
  user: string;
  model: 'groq' | 'gemini';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  status?: 'loading' | 'streaming' | 'completed' | 'error';
  citations?: {
    source_id: string;
    document_id: number;
    document_name: string;
    page_number: number | null;
    chunk_index: number;
    excerpt: string;
    relevance_score: number;
  }[];
}

// ── Activity ───────────────────────────────────────────────────
export type ActivityType =
  | 'document_uploaded'
  | 'query_made'
  | 'ticket_created'
  | 'member_added'
  | 'document_processed'
  | 'ticket_resolved';

export interface ActivityItem {
  id: string;
  type: ActivityType;
  description: string;
  user: string;
  userInitials: string;
  userColor: string;
  timestamp: string;
}

// ── Dashboard ──────────────────────────────────────────────────
export interface StatCard {
  label: string;
  value: string | number;
  change: number;   // percentage, can be negative
  suffix?: string;
}

// ── Workspace ──────────────────────────────────────────────────
export type WorkspacePlan = 'starter' | 'pro' | 'enterprise';

export interface Workspace {
  id: string;
  name: string;
  plan: WorkspacePlan;
}
