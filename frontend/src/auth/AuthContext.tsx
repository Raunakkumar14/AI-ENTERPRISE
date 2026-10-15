import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
  type ReactNode,
} from 'react';
import { ApiError, apiRequest, type ApiUser, type ApiWorkspace } from '../api/client';

interface AuthContextValue {
  token: string | null;
  user: ApiUser | null;
  workspaces: ApiWorkspace[];
  workspace: ApiWorkspace | null;
  ready: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  createWorkspace: (name: string, description: string) => Promise<void>;
  selectWorkspace: (workspaceId: number) => void;
  refreshWorkspaces: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const TOKEN_KEY = 'knowledge-hub-access-token';
const WORKSPACE_KEY = 'knowledge-hub-workspace-id';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<ApiUser | null>(null);
  const [workspaces, setWorkspaces] = useState<ApiWorkspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(() => {
    const value = sessionStorage.getItem(WORKSPACE_KEY);
    return value ? Number(value) : null;
  });
  const [ready, setReady] = useState(!sessionStorage.getItem(TOKEN_KEY));
  const [error, setError] = useState<string | null>(null);

  const loadWorkspaces = useCallback(async (accessToken: string) => {
    const rows = await apiRequest<ApiWorkspace[]>('/workspaces', accessToken);
    setWorkspaces(rows);
    setSelectedWorkspaceId(current => {
      const next = rows.some(row => row.id === current) ? current : rows[0]?.id ?? null;
      if (next === null) sessionStorage.removeItem(WORKSPACE_KEY);
      else sessionStorage.setItem(WORKSPACE_KEY, String(next));
      return next;
    });
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(WORKSPACE_KEY);
    setToken(null);
    setUser(null);
    setWorkspaces([]);
    setSelectedWorkspaceId(null);
    setError(null);
    setReady(true);
  }, []);

  useEffect(() => {
    if (!token) return;
    let active = true;
    Promise.all([
      apiRequest<ApiUser>('/auth/me', token),
      apiRequest<ApiWorkspace[]>('/workspaces', token),
    ]).then(([currentUser, rows]) => {
      if (!active) return;
      setUser(currentUser);
      setWorkspaces(rows);
      setSelectedWorkspaceId(current => {
        const next = rows.some(row => row.id === current) ? current : rows[0]?.id ?? null;
        if (next === null) sessionStorage.removeItem(WORKSPACE_KEY);
        else sessionStorage.setItem(WORKSPACE_KEY, String(next));
        return next;
      });
    }).catch((reason: unknown) => {
      if (!active) return;
      if (reason instanceof ApiError && reason.status === 401) logout();
      else setError(reason instanceof Error ? reason.message : 'Unable to load your account.');
    }).finally(() => {
      if (active) setReady(true);
    });
    return () => { active = false; };
  }, [logout, token]);

  const acceptToken = useCallback(async (accessToken: string) => {
    const [currentUser, rows] = await Promise.all([
      apiRequest<ApiUser>('/auth/me', accessToken),
      apiRequest<ApiWorkspace[]>('/workspaces', accessToken),
    ]);
    sessionStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
    setUser(currentUser);
    setWorkspaces(rows);
    const saved = Number(sessionStorage.getItem(WORKSPACE_KEY));
    const nextId = rows.some(row => row.id === saved) ? saved : rows[0]?.id ?? null;
    setSelectedWorkspaceId(nextId);
    if (nextId === null) sessionStorage.removeItem(WORKSPACE_KEY);
    else sessionStorage.setItem(WORKSPACE_KEY, String(nextId));
    setError(null);
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setReady(false);
    try {
      const result = await apiRequest<{ access_token: string }>('/auth/login', '', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      await acceptToken(result.access_token);
    } catch (reason) {
      setReady(true);
      throw reason;
    }
  }, [acceptToken]);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    setReady(false);
    try {
      await apiRequest('/auth/register', '', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      await login(email, password);
    } catch (reason) {
      setReady(true);
      throw reason;
    }
  }, [login]);

  const createWorkspace = useCallback(async (name: string, description: string) => {
    if (!token) throw new Error('Sign in before creating a workspace.');
    const created = await apiRequest<{ id: number }>('/workspaces', token, {
      method: 'POST',
      body: JSON.stringify({ name, description: description || null }),
    });
    const rows = await apiRequest<ApiWorkspace[]>('/workspaces', token);
    setWorkspaces(rows);
    setSelectedWorkspaceId(created.id);
    sessionStorage.setItem(WORKSPACE_KEY, String(created.id));
  }, [token]);

  const selectWorkspace = useCallback((workspaceId: number) => {
    if (!workspaces.some(row => row.id === workspaceId)) return;
    setSelectedWorkspaceId(workspaceId);
    sessionStorage.setItem(WORKSPACE_KEY, String(workspaceId));
  }, [workspaces]);

  const value = useMemo<AuthContextValue>(() => ({
    token,
    user,
    workspaces,
    workspace: workspaces.find(row => row.id === selectedWorkspaceId) ?? null,
    ready,
    error,
    login,
    register,
    createWorkspace,
    selectWorkspace,
    refreshWorkspaces: async () => { if (token) await loadWorkspaces(token); },
    logout,
  }), [
    token, user, workspaces, selectedWorkspaceId, ready, error, login,
    register, createWorkspace, selectWorkspace, loadWorkspaces, logout,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
