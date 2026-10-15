import { useState, type FormEvent } from 'react';
import { Check, Settings, Shield, Sparkles } from 'lucide-react';
import { apiRequest, workspacePath } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export default function SettingsPage() {
  const { token, workspace, refreshWorkspaces } = useAuth();
  const [name, setName] = useState(workspace?.name ?? '');
  const [description, setDescription] = useState(workspace?.description ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const isAdmin = workspace?.role === 'admin';

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !workspace || !isAdmin) return;
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      await apiRequest(workspacePath(workspace.id), token, {
        method: 'PATCH',
        body: JSON.stringify({ name, description: description || null }),
      });
      await refreshWorkspaces();
      setSaved(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to save workspace settings.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <section className="card card-body">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-600 grid place-items-center"><Settings size={18} /></div>
          <div><h2 className="text-sm font-semibold text-slate-900">Workspace details</h2><p className="text-xs text-slate-500">Changes are saved to the active workspace in PostgreSQL.</p></div>
        </div>
        <form onSubmit={event => void save(event)} className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">Workspace name
            <input required maxLength={255} value={name} onChange={event => setName(event.target.value)} disabled={!isAdmin} className="input mt-1 max-w-lg" />
          </label>
          <label className="block text-sm font-medium text-slate-700">Description
            <textarea maxLength={2000} value={description} onChange={event => setDescription(event.target.value)} disabled={!isAdmin} className="input mt-1 max-w-lg min-h-24" />
          </label>
          <div className="text-xs text-slate-500">Workspace slug: <span className="font-mono">{workspace?.slug}</span> · Your role: <span className="capitalize">{workspace?.role?.replace('_', ' ')}</span></div>
          {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
          {saved && <p role="status" className="flex items-center gap-1 text-sm text-emerald-700"><Check size={14} /> Workspace settings saved.</p>}
          {isAdmin ? <button disabled={busy} className="btn-md btn-primary">{busy ? 'Saving…' : 'Save changes'}</button>
            : <p className="text-sm text-slate-500">Only a workspace administrator can change these details.</p>}
        </form>
      </section>

      <section className="card card-body">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-violet-100 text-violet-600 grid place-items-center"><Sparkles size={18} /></div>
          <div><h2 className="text-sm font-semibold text-slate-900">AI provider configuration</h2><p className="text-xs text-slate-500">Provider credentials are server configuration, not workspace browser settings.</p></div>
        </div>
        <p className="text-sm text-slate-600">The backend uses Gemini for embeddings and the configured Gemini or Groq provider for answer generation. Configure API keys and provider selection in the backend environment, then restart the API. This frontend does not collect or store provider secrets.</p>
      </section>

      <section className="card card-body">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 grid place-items-center"><Shield size={18} /></div>
          <div><h2 className="text-sm font-semibold text-slate-900">Access control</h2><p className="text-xs text-slate-500">Permissions are enforced by the API on every request.</p></div>
        </div>
        <ul className="list-disc pl-5 space-y-1 text-sm text-slate-600">
          <li>Admin: workspace settings and membership administration.</li>
          <li>Support Agent: document uploads and deletion.</li>
          <li>User: workspace document access and AI queries.</li>
        </ul>
        <p className="text-xs text-slate-500 mt-3">Account 2FA, notification preferences, audit logs, billing, and workspace deletion are not implemented by the current backend.</p>
      </section>
    </div>
  );
}
