import { useEffect, useState } from 'react';
import { FileText, MessageSquare, Users } from 'lucide-react';
import StatsCard from '../components/ui/StatsCard';
import { apiRequest, workspacePath, type ApiDocument, type WorkspaceAnalytics } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function OverviewPage() {
  const { token, workspace, user } = useAuth();
  const [analytics, setAnalytics] = useState<WorkspaceAnalytics | null>(null);
  const [recentDocuments, setRecentDocuments] = useState<ApiDocument[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token || !workspace) return;
    let active = true;
    Promise.all([
      apiRequest<WorkspaceAnalytics>(workspacePath(workspace.id, '/analytics'), token),
      apiRequest<{ items: ApiDocument[] }>(workspacePath(workspace.id, '/documents?limit=5'), token),
    ]).then(([data, docs]) => {
      if (!active) return;
      setAnalytics(data);
      setRecentDocuments(docs.items);
      setError('');
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : 'Unable to load workspace analytics.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, workspace]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 rounded-xl p-5 text-white">
        <h2 className="font-semibold text-lg">Welcome, {user?.full_name}</h2>
        <p className="text-indigo-100 text-sm mt-1">
          {workspace?.name} workspace activity, loaded from your database.
        </p>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatsCard label="Documents" value={loading ? '—' : analytics?.document_count ?? 0} icon={FileText} iconBg="bg-indigo-100" iconColor="text-indigo-600" />
        <StatsCard label="AI Conversations" value={loading ? '—' : analytics?.conversation_count ?? 0} icon={MessageSquare} iconBg="bg-violet-100" iconColor="text-violet-600" />
        <StatsCard label="Active Members" value={loading ? '—' : analytics?.active_member_count ?? 0} icon={Users} iconBg="bg-emerald-100" iconColor="text-emerald-600" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="card lg:col-span-2">
          <header className="card-header"><h2 className="card-title">Recently added documents</h2></header>
          {loading ? <p className="p-5 text-sm text-slate-500">Loading activity…</p>
            : recentDocuments.length ? <div className="divide-y divide-slate-100">
              {recentDocuments.map(document => <div key={document.id} className="px-5 py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0"><FileText size={16} className="text-indigo-500 flex-shrink-0" />
                  <div className="min-w-0"><p className="text-sm font-medium text-slate-800 truncate">{document.filename}</p><p className="text-xs text-slate-500">{new Date(document.created_at).toLocaleString()}</p></div>
                </div>
                <span className="text-xs capitalize text-slate-500">{document.status}</span>
              </div>)}
            </div> : <p className="p-5 text-sm text-slate-500">No documents have been uploaded to this workspace.</p>}
        </section>
        <section className="card p-5">
          <h2 className="card-title mb-4">Document processing</h2>
          {loading ? <p className="text-sm text-slate-500">Loading…</p>
            : <dl className="space-y-3 text-sm">
              {['pending', 'processing', 'completed', 'failed'].map(status => <div key={status} className="flex justify-between">
                <dt className="capitalize text-slate-500">{status}</dt><dd className="font-semibold text-slate-800">{analytics?.documents_by_status[status] ?? 0}</dd>
              </div>)}
            </dl>}
        </section>
      </div>
      <p className="text-xs text-slate-500">Support-ticket metrics are omitted because ticket storage and APIs are not implemented in this backend.</p>
    </div>
  );
}
