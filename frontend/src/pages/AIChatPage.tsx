import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Bot, CheckCircle2, CircleStop, LoaderCircle, MessageSquare, Send, X } from 'lucide-react';
import Avatar from '../components/ui/Avatar';
import { apiRequest, workspacePath, type ApiConversation, type ApiDocumentDetail, type ApiMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import type { ChatMessage } from '../types';

type ChatStatus = 'idle' | 'loading' | 'streaming' | 'completed' | 'error';
type Citation = NonNullable<ApiMessage['citations']>[number];
type StreamEvent =
  | { event: 'conversation'; data: { conversation_id: number; title: string } }
  | { event: 'text'; data: { delta: string } }
  | { event: 'citations'; data: { items: Citation[]; insufficient_context: boolean } }
  | { event: 'error'; data: { code: string; message: string } }
  | { event: 'complete'; data: { conversation_id: number; status: 'completed' | 'failed' } };

function parseEvent(frame: string): StreamEvent | null {
  let eventName = '';
  const data: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) eventName = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (!eventName || !data.length) return null;
  return { event: eventName, data: JSON.parse(data.join('\n')) } as StreamEvent;
}

export default function AIChatPage() {
  const { token, workspace } = useAuth();
  const workspaceId = workspace?.id;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<ChatStatus>('idle');
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<ApiDocumentDetail | null>(null);
  const abortController = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const busy = status === 'loading' || status === 'streaming';

  const loadConversations = useCallback(async () => {
    if (!token || !workspaceId) {
      setConversations([]);
      return;
    }
    const result = await apiRequest<{ items: ApiConversation[] }>(
      workspacePath(workspaceId, '/conversations'),
      token,
    );
    setConversations(result.items);
  }, [token, workspaceId]);

  useEffect(() => {
    void loadConversations().catch(reason => {
      setError(reason instanceof Error ? reason.message : 'Unable to load conversations.');
    });
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const openConversation = async (id: number) => {
    if (!token || !workspaceId || busy) return;
    setError('');
    try {
      const detail = await apiRequest<ApiConversation & { messages: ApiMessage[] }>(
        workspacePath(workspaceId, `/conversations/${id}`),
        token,
      );
      setConversationId(detail.id);
      setMessages(detail.messages.map(message => ({
        id: String(message.id),
        role: message.role,
        content: message.content,
        timestamp: message.created_at,
        citations: message.citations,
        status: 'completed',
      })));
      setStatus('idle');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load conversation.');
      setStatus('error');
    }
  };

  const openSource = async (documentId: number) => {
    if (!token || !workspaceId) return;
    try {
      setPreview(await apiRequest<ApiDocumentDetail>(
        workspacePath(workspaceId, `/documents/${documentId}`),
        token,
      ));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load source preview.');
    }
  };

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || !token || !workspaceId || busy) return;
    setError('');
    setInput('');
    setStatus('loading');
    const assistantId = crypto.randomUUID();
    setMessages(previous => [
      ...previous,
      { id: crypto.randomUUID(), role: 'user', content: question, timestamp: new Date().toISOString() },
      { id: assistantId, role: 'assistant', content: '', timestamp: new Date().toISOString(), status: 'loading', citations: [] },
    ]);

    const controller = new AbortController();
    abortController.current = controller;
    let buffer = '';
    let completed = false;
    try {
      const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
      const response = await fetch(`${baseUrl}/api/v1${workspacePath(workspaceId, '/ask/stream')}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ question, conversation_id: conversationId }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
        throw new Error(body?.error?.message ?? `Request failed (${response.status})`);
      }
      if (!response.body) throw new Error('Streaming response is not available in this browser.');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
        let boundary = buffer.indexOf('\n\n');
        while (boundary >= 0) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const event = parseEvent(frame);
          if (event) {
            switch (event.event) {
              case 'conversation':
                setConversationId(event.data.conversation_id);
                break;
              case 'text':
                setStatus('streaming');
                setMessages(previous => previous.map(message => message.id === assistantId
                  ? { ...message, content: message.content + event.data.delta, status: 'streaming' }
                  : message));
                break;
              case 'citations':
                setMessages(previous => previous.map(message => message.id === assistantId
                  ? { ...message, citations: event.data.items }
                  : message));
                break;
              case 'error':
                setError(event.data.message);
                setStatus('error');
                setMessages(previous => previous.map(message => message.id === assistantId
                  ? { ...message, content: event.data.message, status: 'error' }
                  : message));
                break;
              case 'complete':
                completed = true;
                setStatus(event.data.status === 'completed' ? 'completed' : 'error');
                setMessages(previous => previous.map(message => message.id === assistantId
                  ? { ...message, status: event.data.status === 'completed' ? 'completed' : 'error' }
                  : message));
                break;
            }
          }
          boundary = buffer.indexOf('\n\n');
        }
        if (done) break;
      }
      if (!completed) throw new Error('The stream ended before the answer completed.');
      try {
        await loadConversations();
      } catch {
        setError('The answer completed, but conversation history could not be refreshed.');
      }
    } catch (reason) {
      const message = reason instanceof DOMException && reason.name === 'AbortError'
        ? 'Response cancelled. The saved conversation may contain an incomplete turn.'
        : reason instanceof Error ? reason.message : 'Unable to complete the answer.';
      setError(message);
      setStatus('error');
      setMessages(previous => previous.map(item => item.id === assistantId
        ? { ...item, status: 'error' }
        : item));
    } finally {
      abortController.current = null;
    }
  };

  const startNewConversation = () => {
    if (busy) return;
    setConversationId(null);
    setMessages([]);
    setError('');
    setStatus('idle');
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem-3rem)] max-w-7xl mx-auto gap-4">
      <aside className="hidden lg:flex flex-col w-64 flex-shrink-0 card overflow-hidden">
        <div className="card-header flex-shrink-0">
          <h2 className="card-title">Conversations</h2>
          <button className="btn-sm btn-primary" onClick={startNewConversation} disabled={busy}>New</button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
          {conversations.map(conversation => (
            <button key={conversation.id} onClick={() => void openConversation(conversation.id)} disabled={busy}
              className={`w-full text-left px-4 py-3 hover:bg-slate-50 ${conversation.id === conversationId ? 'bg-indigo-50' : ''}`}>
              <p className="text-xs font-medium text-slate-800 line-clamp-1">{conversation.title}</p>
              <p className="text-[11px] text-slate-400 mt-1">{new Date(conversation.updated_at).toLocaleString()}</p>
            </button>
          ))}
          {conversations.length === 0 && <p className="p-4 text-xs text-slate-500">No saved conversations yet.</p>}
        </div>
      </aside>

      <section className="flex-1 flex flex-col card overflow-hidden min-w-0">
        <div className="card-header flex-shrink-0 gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center"><Bot size={15} className="text-white" /></div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">{conversations.find(item => item.id === conversationId)?.title ?? 'New conversation'}</p>
              <p className="text-[11px] text-slate-400">{workspace?.name ?? 'No workspace selected'}</p>
            </div>
          </div>
          <button className="btn-sm btn-secondary lg:hidden" onClick={() => void loadConversations()} aria-label="Refresh conversations"><MessageSquare size={14} /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {!messages.length && <div className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500 text-center">
            Ask a question about documents processed in this workspace. Answers include citations from retrieved chunks.
          </div>}
          {messages.map(message => (
            <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {message.role === 'assistant'
                ? <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"><Bot size={14} className="text-white" /></div>
                : <Avatar initials="You" colorClass="bg-indigo-600" size="sm" />}
              <div className={`max-w-[80%] flex flex-col gap-1 ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${message.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'}`}>
                  {message.content || (message.status === 'loading' ? 'Searching your workspace…' : '')}
                  {message.status === 'streaming' && <span className="inline-block w-1.5 h-4 ml-1 align-middle bg-indigo-500 animate-pulse" />}
                </div>
                {!!message.citations?.length && <div className="space-y-1 mt-1">
                  {message.citations.map(citation => <button key={citation.source_id} onClick={() => void openSource(citation.document_id)} className="block text-left text-[11px] text-slate-600 border-l-2 border-indigo-300 pl-2 hover:bg-indigo-50 rounded-r">
                    <span className="font-medium text-indigo-700 underline">{citation.document_name}</span>{citation.page_number !== null && ` · page ${citation.page_number}`}
                    <p className="text-slate-500 line-clamp-3">{citation.excerpt}</p>
                  </button>)}
                </div>}
                <div className="flex items-center gap-1.5 px-1 text-[10px] text-slate-400">
                  <span>{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  {message.status === 'loading' && <span>· searching</span>}
                  {message.status === 'streaming' && <span>· streaming</span>}
                  {message.status === 'completed' && <span className="inline-flex items-center gap-1 text-emerald-600"><CheckCircle2 size={11} /> completed</span>}
                  {message.status === 'error' && <span className="inline-flex items-center gap-1 text-red-600"><AlertCircle size={11} /> error</span>}
                </div>
              </div>
            </div>
          ))}
          {error && <div role="alert" className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-100 p-3 text-xs text-red-700"><AlertCircle size={14} />{error}</div>}
          <div ref={bottomRef} />
        </div>
        <div className="border-t border-slate-200 p-4 flex-shrink-0">
          <div className="flex items-end gap-2">
            <textarea value={input} onChange={event => setInput(event.target.value)}
              onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }}
              placeholder="Ask anything about your workspace documents…" rows={1} disabled={!workspaceId || busy}
              className="flex-1 resize-none input py-2.5 max-h-32 overflow-y-auto disabled:bg-slate-50" />
            {busy
              ? <button onClick={() => abortController.current?.abort()} className="btn-sm p-2.5 bg-red-50 text-red-700" aria-label="Stop response">
                {status === 'loading' ? <LoaderCircle size={15} className="animate-spin" /> : <CircleStop size={15} />}
              </button>
              : <button onClick={() => void sendMessage()} disabled={!input.trim() || !workspaceId} className="btn-sm btn-primary p-2.5" aria-label="Send"><Send size={15} /></button>}
          </div>
          <p className="text-[10px] text-slate-400 mt-2 text-center">Answers are grounded in your documents. Verify important information.</p>
        </div>
      </section>
      {preview && <div className="fixed inset-0 z-50 bg-slate-900/40 p-3 sm:p-8 grid place-items-center" onClick={() => setPreview(null)}>
        <section role="dialog" aria-modal="true" aria-label={`Preview ${preview.filename}`} className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col" onClick={event => event.stopPropagation()}>
          <header className="flex items-center gap-3 p-4 border-b border-slate-200">
            <div className="flex-1 min-w-0"><h2 className="font-semibold text-slate-900 truncate">{preview.filename}</h2><p className="text-xs text-slate-500">Extracted text preview</p></div>
            <button onClick={() => setPreview(null)} className="p-2 text-slate-500 hover:text-slate-900" aria-label="Close preview"><X size={18} /></button>
          </header>
          <div className="overflow-y-auto p-4 space-y-3">{preview.chunks.map(chunk => <article key={chunk.id} className="border border-slate-200 rounded-lg p-3">
            <div className="text-[11px] font-medium text-slate-500 mb-2">Chunk {chunk.chunk_index + 1}{chunk.page_number !== null ? ` · page ${chunk.page_number}` : ''}</div>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{chunk.content}</p>
          </article>)}</div>
        </section>
      </div>}
    </div>
  );
}
