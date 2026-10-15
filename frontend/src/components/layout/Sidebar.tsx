// src/components/layout/Sidebar.tsx
import { useState, type FormEvent } from 'react';
import {
  LayoutDashboard, Bot, FileText, MessageSquare, LifeBuoy,
  Users, Settings, ChevronLeft, ChevronRight, ChevronDown,
  Building2, Check, LogOut, Plus,
} from 'lucide-react';
import type { NavPage, Workspace } from '../../types';
import { useAuth } from '../../auth/AuthContext';

const NAV_ITEMS: { id: NavPage; label: string; icon: typeof LayoutDashboard; badge?: number }[] = [
  { id: 'overview',         label: 'Overview',        icon: LayoutDashboard },
  { id: 'ai-chat',          label: 'AI Chat',          icon: Bot },
  { id: 'documents',        label: 'Documents',        icon: FileText },
  { id: 'conversations',    label: 'Conversations',    icon: MessageSquare },
  { id: 'support-tickets',  label: 'Support Tickets',  icon: LifeBuoy },
  { id: 'team',             label: 'Team',             icon: Users },
  { id: 'settings',         label: 'Settings',         icon: Settings },
];

const PLAN_COLORS: Record<Workspace['plan'], string> = {
  starter:    'bg-slate-100 text-slate-600',
  pro:        'bg-blue-100  text-blue-700',
  enterprise: 'bg-indigo-100 text-indigo-700',
};

interface SidebarProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export default function Sidebar({
  currentPage, onNavigate, collapsed, onToggleCollapse, mobileOpen, onCloseMobile,
}: SidebarProps) {
  const { user, workspace, workspaces, selectWorkspace, createWorkspace, logout } = useAuth();
  const [workspaceError, setWorkspaceError] = useState('');
  const [createWorkspaceOpen, setCreateWorkspaceOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState('');
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [wsOpen, setWsOpen]       = useState(false);
  const [userOpen, setUserOpen]   = useState(false);
  const initials = user?.full_name.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase() ?? 'U';

  const navigate = (page: NavPage) => { onNavigate(page); onCloseMobile(); };
  const submitWorkspace = async (event: FormEvent) => {
    event.preventDefault();
    setCreatingWorkspace(true);
    setWorkspaceError('');
    try {
      await createWorkspace(newWorkspaceName, newWorkspaceDescription);
      setNewWorkspaceName('');
      setNewWorkspaceDescription('');
      setCreateWorkspaceOpen(false);
      setWsOpen(false);
    } catch (reason) {
      setWorkspaceError(reason instanceof Error ? reason.message : 'Could not create workspace.');
    } finally {
      setCreatingWorkspace(false);
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside className={`
        fixed inset-y-0 left-0 z-30 flex flex-col bg-white border-r border-slate-200
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-60'}
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>

        {/* ── Logo ─────────────────────────────────────────── */}
        <div className={`flex items-center h-14 border-b border-slate-200 px-3 flex-shrink-0
          ${collapsed ? 'justify-center' : 'justify-between'}`}>
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white text-[11px] font-bold tracking-tight">KH</span>
            </div>
            {!collapsed && (
              <span className="font-semibold text-slate-900 text-sm truncate">Knowledge Hub</span>
            )}
          </div>
          {!collapsed && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex w-6 h-6 items-center justify-center rounded-md
                         text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors flex-shrink-0"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft size={14} />
            </button>
          )}
        </div>

        {/* Expand button when collapsed */}
        {collapsed && (
          <div className="hidden lg:flex justify-center px-2 pt-2 pb-1 border-b border-slate-200">
            <button
              onClick={onToggleCollapse}
              className="w-8 h-8 flex items-center justify-center rounded-lg
                         text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Expand sidebar"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}

        {/* ── Workspace selector ─────────────────────────── */}
        {!collapsed && (
          <div className="relative px-2 py-2 border-b border-slate-200">
            <button
              onClick={() => setWsOpen(!wsOpen)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg
                         hover:bg-slate-50 transition-colors text-left"
            >
              <div className="w-6 h-6 bg-indigo-100 rounded-md flex items-center justify-center flex-shrink-0">
                <Building2 size={13} className="text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-slate-900 truncate">{workspace?.name ?? 'Choose workspace'}</div>
                <div className={`text-[10px] mt-0.5 px-1.5 py-px rounded-full inline-block font-medium ${PLAN_COLORS[workspace?.plan ?? 'starter']}`}>
                  {workspace?.plan ?? 'starter'}
                </div>
              </div>
              <ChevronDown size={12} className={`text-slate-400 flex-shrink-0 transition-transform ${wsOpen ? 'rotate-180' : ''}`} />
            </button>

            {wsOpen && (
              <div className="absolute left-2 right-2 top-full mt-1 bg-white border border-slate-200
                              rounded-xl shadow-lg shadow-slate-200/50 z-50 overflow-hidden py-1">
                {workspaceError && <p role="alert" className="px-3 py-1 text-xs text-red-600">{workspaceError}</p>}
                {workspaces.map(ws => (
                  <button
                    key={ws.id}
                    onClick={() => { selectWorkspace(ws.id); setWsOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 transition-colors text-left"
                  >
                    <div className="w-6 h-6 bg-indigo-100 rounded-md flex items-center justify-center flex-shrink-0">
                      <Building2 size={12} className="text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-slate-900 truncate">{ws.name}</div>
                      <div className={`text-[10px] px-1.5 py-px rounded-full inline-block font-medium mt-0.5 ${PLAN_COLORS[ws.plan]}`}>
                        {ws.plan}
                      </div>
                    </div>
                    {ws.id === workspace?.id && <Check size={12} className="text-indigo-600" />}
                  </button>
                ))}
                <div className="border-t border-slate-100 mt-1 pt-1 px-2">
                  <button onClick={() => setCreateWorkspaceOpen(true)} className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg
                                     text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors">
                    <Plus size={12} /> Create workspace
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Navigation ─────────────────────────────────── */}
        <nav className="flex-1 px-2 py-2 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ id, label, icon: Icon, badge }) => {
            const active = currentPage === id;
            return (
              <button
                key={id}
                onClick={() => navigate(id)}
                title={collapsed ? label : undefined}
                className={`sidebar-link ${collapsed ? 'justify-center px-0 py-2.5' : ''} ${active ? 'sidebar-link-active' : ''}`}
              >
                <Icon size={18} className="flex-shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1 text-left">{label}</span>
                    {badge && (
                      <span className="ml-auto bg-red-100 text-red-600 text-[10px] font-bold
                                       px-1.5 py-0.5 rounded-full leading-none">
                        {badge}
                      </span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        {/* ── User profile ────────────────────────────────── */}
        <div className="border-t border-slate-200 p-2 flex-shrink-0 relative">
          {collapsed ? (
            <button
              title={`Sign out ${user?.full_name ?? ''}`}
              aria-label="Sign out"
              onClick={logout}
              className="w-full flex items-center justify-center py-2 rounded-lg
                         hover:bg-slate-100 transition-colors"
            >
              <div className="w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center">
                <span className="text-white text-[11px] font-semibold">{initials}</span>
              </div>
            </button>
          ) : (
            <>
              <button
                onClick={() => setUserOpen(!userOpen)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg
                           hover:bg-slate-50 transition-colors text-left"
              >
                <div className="w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-[11px] font-semibold">{initials}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-slate-900 truncate">{user?.full_name}</div>
                  <div className="text-[10px] text-slate-500 truncate">{user?.email}</div>
                </div>
                <ChevronDown size={12} className={`text-slate-400 transition-transform ${userOpen ? 'rotate-180' : ''}`} />
              </button>

              {userOpen && (
                <div className="absolute bottom-full left-2 right-2 mb-2 bg-white border border-slate-200
                                rounded-xl shadow-lg shadow-slate-200/50 z-50 overflow-hidden py-1">
                  <div className="px-3 py-2 border-b border-slate-100">
                    <div className="text-xs font-semibold text-slate-900">{user?.full_name}</div>
                    <div className="text-[11px] text-slate-500">{user?.email}</div>
                    <span className="text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium mt-1 inline-block">{workspace?.role}</span>
                  </div>
                  <div className="border-t border-slate-100 mt-1 pt-1" />
                  <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 hover:bg-red-50 transition-colors text-xs text-red-600">
                    <LogOut size={13} /> Sign out
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </aside>
      {createWorkspaceOpen && <div className="fixed inset-0 z-50 bg-slate-900/40 grid place-items-center p-4" onClick={() => setCreateWorkspaceOpen(false)}>
        <form onSubmit={event => void submitWorkspace(event)} className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4" onClick={event => event.stopPropagation()}>
          <h2 className="font-semibold text-slate-900">Create workspace</h2>
          <label className="block text-sm text-slate-700">Workspace name
            <input required maxLength={255} value={newWorkspaceName} onChange={event => setNewWorkspaceName(event.target.value)} className="input mt-1" />
          </label>
          <label className="block text-sm text-slate-700">Description <span className="text-slate-400">(optional)</span>
            <textarea maxLength={2000} value={newWorkspaceDescription} onChange={event => setNewWorkspaceDescription(event.target.value)} className="input mt-1 min-h-20" />
          </label>
          {workspaceError && <p role="alert" className="text-sm text-red-600">{workspaceError}</p>}
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setCreateWorkspaceOpen(false)} className="btn-md btn-secondary">Cancel</button>
            <button disabled={creatingWorkspace} className="btn-md btn-primary">{creatingWorkspace ? 'Creating…' : 'Create workspace'}</button></div>
        </form>
      </div>}
    </>
  );
}
