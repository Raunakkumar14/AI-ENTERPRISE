import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Mail, Search, UserPlus, Users, Trash2 } from 'lucide-react';
import EmptyState from '../components/ui/EmptyState';
import { apiRequest, workspacePath, type ApiMember } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type WorkspaceRole = ApiMember['role'];
const ROLE_OPTIONS: WorkspaceRole[] = ['admin', 'support_agent', 'user'];

export default function TeamPage() {
  const { token, workspace } = useAuth();
  const workspaceId = workspace?.id;
  const isAdmin = workspace?.role === 'admin';
  const [members, setMembers] = useState<ApiMember[]>([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<WorkspaceRole | 'all'>('all');
  const [showAdd, setShowAdd] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<WorkspaceRole>('user');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadMembers = useCallback(async () => {
    if (!token || !workspaceId) return;
    const rows = await apiRequest<ApiMember[]>(workspacePath(workspaceId, '/members'), token);
    setMembers(rows);
  }, [token, workspaceId]);

  useEffect(() => {
    void loadMembers().catch(reason => setError(reason instanceof Error ? reason.message : 'Unable to load members.'));
  }, [loadMembers]);

  const filtered = useMemo(() => members.filter(member => {
    const term = search.trim().toLowerCase();
    const matches = !term || member.full_name.toLowerCase().includes(term) || member.email.toLowerCase().includes(term);
    return matches && (roleFilter === 'all' || member.role === roleFilter);
  }), [members, search, roleFilter]);

  const addMember = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !workspaceId) return;
    setBusy(true);
    setError('');
    try {
      await apiRequest(workspacePath(workspaceId, '/members'), token, {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      });
      await loadMembers();
      setEmail('');
      setRole('user');
      setShowAdd(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to add member.');
    } finally {
      setBusy(false);
    }
  };

  const updateRole = async (member: ApiMember, nextRole: WorkspaceRole) => {
    if (!token || !workspaceId || nextRole === member.role) return;
    try {
      const updated = await apiRequest<ApiMember>(workspacePath(workspaceId, `/members/${member.user_id}`), token, {
        method: 'PATCH',
        body: JSON.stringify({ role: nextRole }),
      });
      setMembers(rows => rows.map(row => row.user_id === member.user_id ? updated : row));
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to update member role.');
    }
  };

  const removeMember = async (member: ApiMember) => {
    if (!token || !workspaceId || !window.confirm(`Remove ${member.full_name} from this workspace?`)) return;
    try {
      await apiRequest<void>(workspacePath(workspaceId, `/members/${member.user_id}`), token, { method: 'DELETE' });
      setMembers(rows => rows.filter(row => row.user_id !== member.user_id));
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to remove member.');
    }
  };

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search name or email…" className="input pl-9" />
        </div>
        <select value={roleFilter} onChange={event => setRoleFilter(event.target.value as WorkspaceRole | 'all')} className="input-sm min-w-36">
          <option value="all">All roles</option>{ROLE_OPTIONS.map(value => <option key={value} value={value}>{value.replace('_', ' ')}</option>)}
        </select>
        {isAdmin && <button onClick={() => setShowAdd(true)} className="btn-md btn-primary ml-auto"><UserPlus size={15} /> Add member</button>}
      </div>
      {!isAdmin && <p className="text-xs text-slate-500">Only workspace administrators can add, remove, or change member roles.</p>}
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      <p className="text-xs text-slate-500"><strong className="text-slate-700">{members.length}</strong> workspace members</p>
      <div className="card">
        {!members.length ? <EmptyState icon={Users} title="No members found" description="This workspace has no listed memberships." />
          : <div className="table-wrapper"><table className="table">
            <thead><tr><th className="th">Member</th><th className="th">Role</th><th className="th hidden sm:table-cell">Joined</th>{isAdmin && <th className="th w-12" />}</tr></thead>
            <tbody>{filtered.map(member => <tr key={member.user_id} className="tr-hover">
              <td className="td"><div className="flex items-center gap-3 min-w-0">
                <span className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 grid place-items-center text-xs font-semibold">{member.full_name.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase()}</span>
                <span className="min-w-0"><span className="block text-sm font-medium text-slate-800">{member.full_name}</span>
                  <a href={`mailto:${member.email}`} className="flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600"><Mail size={11} />{member.email}</a></span>
              </div></td>
              <td className="td">{isAdmin
                ? <select aria-label={`Role for ${member.email}`} value={member.role} onChange={event => void updateRole(member, event.target.value as WorkspaceRole)} className="input-sm">
                  {ROLE_OPTIONS.map(value => <option key={value} value={value}>{value.replace('_', ' ')}</option>)}
                </select>
                : <span className="text-xs capitalize text-slate-600">{member.role.replace('_', ' ')}</span>}</td>
              <td className="td hidden sm:table-cell text-xs text-slate-500">{new Date(member.joined_at).toLocaleDateString()}</td>
              {isAdmin && <td className="td"><button title="Remove member" onClick={() => void removeMember(member)} className="p-1.5 text-slate-400 hover:text-red-600"><Trash2 size={14} /></button></td>}
            </tr>)}</tbody>
          </table></div>}
        {members.length > 0 && filtered.length === 0 && <div className="p-5 text-sm text-slate-500">No members match these filters.</div>}
      </div>
      {showAdd && <div className="fixed inset-0 z-50 bg-slate-900/40 grid place-items-center p-4" onClick={() => setShowAdd(false)}>
        <form onSubmit={event => void addMember(event)} className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4" onClick={event => event.stopPropagation()}>
          <h2 className="font-semibold text-slate-900">Add an existing user</h2>
          <p className="text-xs text-slate-500">The user must register before they can be added. This endpoint does not send invitation emails.</p>
          <label className="block text-sm text-slate-700">Email<input required type="email" value={email} onChange={event => setEmail(event.target.value)} className="input mt-1" /></label>
          <label className="block text-sm text-slate-700">Role<select value={role} onChange={event => setRole(event.target.value as WorkspaceRole)} className="input mt-1">
            {ROLE_OPTIONS.map(value => <option key={value} value={value}>{value.replace('_', ' ')}</option>)}
          </select></label>
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setShowAdd(false)} className="btn-md btn-secondary">Cancel</button>
            <button disabled={busy} className="btn-md btn-primary">{busy ? 'Adding…' : 'Add member'}</button></div>
        </form>
      </div>}
    </div>
  );
}
