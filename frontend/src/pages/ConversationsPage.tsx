import { useCallback, useEffect, useMemo, useState } from 'react';
import { FileText, MessageSquare, Search, X } from 'lucide-react';
import EmptyState from '../components/ui/EmptyState';
import { apiRequest, workspacePath, type ApiConversation, type ApiDocumentDetail, type ApiMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function ConversationsPage() {
  const { token, workspace } = useAuth();
  const [items, setItems] = useState<ApiConversation[]>([]);
  const [selected, setSelected] = useState<(ApiConversation & { messages: ApiMessage[] }) | null>(null);
  const [search, setSearch] = useState('');
  const [preview, setPreview] = useState<ApiDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!token || !workspace) return;
    const result = await apiRequest<{ items: ApiConversation[] }>(workspacePath(workspace.id, '/conversations'), token);
    setItems(result.items);
  }, [token, workspace]);

  useEffect(() => {
    let active = true;
    load().catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Unable to load conversations.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [load]);

  const filtered = useMemo(() => items.filter(item => item.title.toLowerCase().includes(search.toLowerCase())), [items, search]);

  const open = async (conversation: ApiConversation) => {
    if (!token || !workspace) return;
    setError('');
    try {
      const detail = await apiRequest<ApiConversation & { messages: ApiMessage[] }>(
        workspacePath(workspace.id, `/conversations/${conversation.id}`), token,
      );
      setSelected(detail);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load conversation details.');
    }
  };

  const openSource = async (documentId: number) => {
    if (!token || !workspace) return;
    try {
      setPreview(await apiRequest<ApiDocumentDetail>(workspacePath(workspace.id, `/documents/${documentId}`), token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load source preview.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex gap-3">
        <div className="relative flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search conversation titles…" className="input pl-9" />
        </div>
        <span className="self-center text-xs text-slate-500">{filtered.length} conversations</span>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        <div className="card divide-y divide-slate-100 lg:col-span-1">
          {loading ? <p className="p-5 text-sm text-slate-500">Loading conversations…</p>
            : filtered.length === 0 ? <EmptyState icon={MessageSquare} title="No conversations found" description="Start a chat to save a conversation here." />
              : filtered.map(item => <button key={item.id} onClick={() => void open(item)} className={`w-full text-left px-4 py-3 hover:bg-slate-50 ${selected?.id === item.id ? 'bg-indigo-50' : ''}`}>
                <p className="text-sm font-medium text-slate-800 line-clamp-2">{item.title}</p>
                <p className="text-xs text-slate-500 mt-1">Updated {new Date(item.updated_at).toLocaleString()}</p>
              </button>)}
        </div>
        <section className="card lg:col-span-2 min-h-52">
          {!selected ? <p className="p-6 text-sm text-slate-500">Select a conversation to view its saved messages and citations.</p>
            : <><header className="card-header"><h2 className="card-title truncate">{selected.title}</h2></header>
              <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
                {selected.messages.map(message => <article key={message.id} className={`rounded-lg p-3 ${message.role === 'user' ? 'bg-indigo-50 ml-6' : 'bg-slate-50 mr-6'}`}>
                  <div className="flex justify-between gap-2"><span className="text-xs font-semibold capitalize text-slate-700">{message.role}</span><time className="text-[10px] text-slate-400">{new Date(message.created_at).toLocaleString()}</time></div>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap mt-2">{message.content}</p>
                  {!!message.citations?.length && <div className="mt-3 space-y-2">{message.citations.map(citation => <button key={citation.source_id} onClick={() => void openSource(citation.document_id)} className="block text-left border-l-2 border-indigo-300 pl-2 text-xs hover:bg-white rounded-r">
                    <span className="font-medium text-indigo-700 inline-flex items-center gap-1"><FileText size={12} />{citation.document_name}</span>
                    {citation.page_number !== null && <span className="text-slate-500"> · page {citation.page_number}</span>}
                    <p className="text-slate-500 line-clamp-2 mt-0.5">{citation.excerpt}</p>
                  </button>)}</div>}
                </article>)}
                {!selected.messages.length && <p className="text-sm text-slate-500">No messages are saved in this conversation.</p>}
              </div></>}
        </section>
      </div>
      {preview && <div className="fixed inset-0 z-50 bg-slate-900/40 p-3 sm:p-8 grid place-items-center" onClick={() => setPreview(null)}>
        <section role="dialog" aria-modal="true" className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col" onClick={event => event.stopPropagation()}>
          <header className="flex items-center p-4 border-b border-slate-200"><div className="flex-1"><h2 className="font-semibold text-slate-900">{preview.filename}</h2><p className="text-xs text-slate-500">Extracted text preview</p></div><button onClick={() => setPreview(null)} aria-label="Close source preview"><X size={18} /></button></header>
          <div className="overflow-y-auto p-4 space-y-3">{preview.chunks.map(chunk => <article key={chunk.id} className="border rounded-lg p-3"><p className="text-[11px] text-slate-500 mb-2">Chunk {chunk.chunk_index + 1}{chunk.page_number ? ` · page ${chunk.page_number}` : ''}</p><p className="text-sm text-slate-700 whitespace-pre-wrap">{chunk.content}</p></article>)}</div>
        </section>
      </div>}
    </div>
  );
}
