import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { FileText, File, Filter, Search, Trash2, Upload, X } from 'lucide-react';
import EmptyState from '../components/ui/EmptyState';
import { apiRequest, workspacePath, type ApiDocument, type ApiDocumentDetail } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type StatusFilter = ApiDocument['status'] | 'all';

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(status: ApiDocument['status']): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function DocumentsPage() {
  const { token, workspace } = useAuth();
  const workspaceId = workspace?.id;
  const canManage = workspace?.role === 'admin' || workspace?.role === 'support_agent';
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [preview, setPreview] = useState<ApiDocumentDetail | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!token || !workspaceId) return;
    const result = await apiRequest<{ items: ApiDocument[] }>(
      workspacePath(workspaceId, '/documents?limit=100'),
      token,
    );
    setDocuments(result.items);
  }, [token, workspaceId]);

  useEffect(() => {
    let active = true;
    loadDocuments().catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : 'Unable to load documents.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [loadDocuments]);

  useEffect(() => {
    if (!documents.some(document => document.status === 'pending' || document.status === 'processing')) return;
    const timer = window.setInterval(() => {
      void loadDocuments().catch(reason => setError(reason instanceof Error ? reason.message : 'Unable to refresh processing status.'));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [documents, loadDocuments]);

  const filtered = useMemo(() => documents.filter(document =>
    document.filename.toLowerCase().includes(search.toLowerCase())
    && (statusFilter === 'all' || document.status === statusFilter),
  ), [documents, search, statusFilter]);

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !token || !workspaceId) return;
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'md', 'markdown', 'txt'].includes(extension ?? '')) {
      setError('Only PDF, Markdown, and plain-text files are supported.');
      return;
    }
    setUploading(true);
    setError('');
    setNotice('');
    const body = new FormData();
    body.append('file', file);
    try {
      await apiRequest<ApiDocument>(workspacePath(workspaceId, '/documents'), token, { method: 'POST', body });
      setNotice('Upload accepted. Document processing has started.');
      await loadDocuments();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const openPreview = async (document: ApiDocument) => {
    if (!token || !workspaceId) return;
    setError('');
    try {
      const detail = await apiRequest<ApiDocumentDetail>(workspacePath(workspaceId, `/documents/${document.id}`), token);
      setPreview(detail);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load document preview.');
    }
  };

  const deleteDocument = async (document: ApiDocument) => {
    if (!token || !workspaceId || !window.confirm(`Delete "${document.filename}" and its extracted chunks?`)) return;
    try {
      await apiRequest<void>(workspacePath(workspaceId, `/documents/${document.id}`), token, { method: 'DELETE' });
      setDocuments(rows => rows.filter(row => row.id !== document.id));
      if (preview?.id === document.id) setPreview(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to delete document.');
    }
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search documents…" className="input pl-9" />
        </div>
        <div className="relative">
          <Filter size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <select value={statusFilter} onChange={event => setStatusFilter(event.target.value as StatusFilter)} className="input-sm pl-7 pr-8 appearance-none cursor-pointer">
            <option value="all">All status</option>
            <option value="pending">Pending</option><option value="processing">Processing</option>
            <option value="completed">Completed</option><option value="failed">Failed</option>
          </select>
        </div>
        {canManage && <label className={`btn-md btn-primary ml-auto cursor-pointer ${uploading ? 'opacity-60 pointer-events-none' : ''}`}>
          <Upload size={15} /> {uploading ? 'Uploading…' : 'Upload'}
          <input type="file" accept=".pdf,.md,.markdown,.txt,application/pdf,text/markdown,text/plain" className="sr-only" disabled={uploading} onChange={event => void upload(event)} />
        </label>}
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</div>}

      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
        <span><strong className="text-slate-700">{filtered.length}</strong> documents</span>
        {(['pending', 'processing', 'completed', 'failed'] as const).map(status => (
          <span key={status}><strong className="text-slate-700">{documents.filter(doc => doc.status === status).length}</strong> {status}</span>
        ))}
      </div>

      <div className="card">
        {loading ? <p className="p-8 text-center text-sm text-slate-500">Loading workspace documents…</p>
          : filtered.length === 0 ? <EmptyState icon={FileText} title={documents.length ? 'No matching documents' : 'No documents yet'} description={documents.length ? 'Try changing the search or status filter.' : canManage ? 'Upload a PDF, Markdown, or text file to build this workspace knowledge base.' : 'A workspace administrator or support agent can upload documents.'} />
            : <div className="table-wrapper"><table className="table">
              <thead><tr><th className="th">Document</th><th className="th hidden sm:table-cell">Type / size</th><th className="th hidden md:table-cell">Added</th><th className="th">Status</th><th className="th hidden lg:table-cell text-right">Chunks</th><th className="th w-16" /></tr></thead>
              <tbody>{filtered.map(document => <tr key={document.id} className="tr-hover">
                <td className="td"><button onClick={() => void openPreview(document)} className="flex items-center gap-2.5 text-left min-w-0">
                  <span className="w-8 h-8 bg-slate-100 rounded-lg grid place-items-center flex-shrink-0">{document.file_type === 'text' ? <File size={16} className="text-slate-500" /> : <FileText size={16} className="text-indigo-500" />}</span>
                  <span className="font-medium text-slate-800 text-xs truncate max-w-[260px] hover:text-indigo-600">{document.filename}</span>
                </button></td>
                <td className="td hidden sm:table-cell text-slate-500 text-xs uppercase">{document.file_type} · {formatSize(document.file_size_bytes)}</td>
                <td className="td hidden md:table-cell text-slate-500 text-xs">{new Date(document.created_at).toLocaleDateString()}</td>
                <td className="td"><span className={`badge ${document.status === 'completed' ? 'badge-green' : document.status === 'failed' ? 'badge-red' : 'badge-blue'}`}>{statusLabel(document.status)}</span>
                  {document.error_message && <p className="text-[10px] text-red-600 mt-1">{document.error_message}</p>}</td>
                <td className="td hidden lg:table-cell text-right text-slate-500 text-xs">{document.chunk_count}</td>
                <td className="td"><div className="flex gap-1">
                  <button onClick={() => void openPreview(document)} className="text-xs text-indigo-600 hover:underline">Preview</button>
                  {canManage && <button onClick={() => void deleteDocument(document)} title="Delete document" className="p-1 text-slate-400 hover:text-red-600"><Trash2 size={14} /></button>}
                </div></td>
              </tr>)}</tbody>
            </table></div>}
      </div>

      {preview && <div className="fixed inset-0 z-50 bg-slate-900/40 p-3 sm:p-8 grid place-items-center" onClick={() => setPreview(null)}>
        <section role="dialog" aria-modal="true" aria-label={`Preview ${preview.filename}`} className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col" onClick={event => event.stopPropagation()}>
          <header className="flex items-center gap-3 p-4 border-b border-slate-200">
            <div className="flex-1 min-w-0"><h2 className="font-semibold text-slate-900 truncate">{preview.filename}</h2><p className="text-xs text-slate-500">{statusLabel(preview.status)} · {preview.chunk_count} chunks · {preview.page_count ?? 'Page data unavailable'}</p></div>
            <button onClick={() => setPreview(null)} className="p-2 text-slate-500 hover:text-slate-900" aria-label="Close preview"><X size={18} /></button>
          </header>
          <div className="overflow-y-auto p-4 space-y-3">
            <p className="text-xs text-slate-500">Preview contains extracted text; original uploads are not retained for file rendering.</p>
            {preview.chunks.length ? preview.chunks.map(chunk => <article key={chunk.id} className="border border-slate-200 rounded-lg p-3">
              <div className="text-[11px] font-medium text-slate-500 mb-2">Chunk {chunk.chunk_index + 1}{chunk.page_number !== null ? ` · page ${chunk.page_number}` : ''}</div>
              <p className="text-sm text-slate-700 whitespace-pre-wrap">{chunk.content}</p>
            </article>) : <p className="text-sm text-slate-500">No extracted text is available yet.</p>}
          </div>
        </section>
      </div>}
    </div>
  );
}
