import { useState, type FormEvent } from 'react';
import { useAuth } from './AuthContext';

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { token, user, workspace, ready, error, login, register, createWorkspace, logout } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceDescription, setWorkspaceDescription] = useState('');

  if (!ready) {
    return <div className="min-h-screen grid place-items-center text-sm text-slate-500">Loading your workspace…</div>;
  }
  if (token && user && workspace) return <>{children}</>;

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError('');
    try {
      if (isRegister) await register(email, password, fullName);
      else await login(email, password);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : 'Unable to authenticate.');
    } finally {
      setBusy(false);
    }
  };

  const submitWorkspace = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError('');
    try {
      await createWorkspace(workspaceName, workspaceDescription);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : 'Unable to create workspace.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 grid place-items-center p-4">
      <section className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-sm p-7">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl grid place-items-center text-white font-bold">KH</div>
          <div><h1 className="text-lg font-semibold text-slate-900">Knowledge Hub</h1><p className="text-xs text-slate-500">Secure workspace access</p></div>
        </div>
        {user && token ? (
          <>
            <h2 className="text-base font-semibold text-slate-900">Create your first workspace</h2>
            <p className="text-sm text-slate-500 mt-1 mb-5">Signed in as {user.email}. Set up a workspace to continue.</p>
            <form onSubmit={submitWorkspace} className="space-y-4">
              <label className="block text-sm text-slate-700">Workspace name
                <input required maxLength={255} value={workspaceName} onChange={event => setWorkspaceName(event.target.value)} className="input mt-1" />
              </label>
              <label className="block text-sm text-slate-700">Description <span className="text-slate-400">(optional)</span>
                <textarea maxLength={2000} value={workspaceDescription} onChange={event => setWorkspaceDescription(event.target.value)} className="input mt-1 min-h-20" />
              </label>
              {(formError || error) && <p role="alert" className="text-sm text-red-600">{formError || error}</p>}
              <button disabled={busy} className="btn-md btn-primary w-full justify-center">{busy ? 'Creating…' : 'Create workspace'}</button>
            </form>
            <button onClick={logout} className="mt-4 text-sm text-slate-500 hover:text-slate-800">Sign out</button>
          </>
        ) : (
          <>
            <h2 className="text-base font-semibold text-slate-900">{isRegister ? 'Create your account' : 'Sign in'}</h2>
            <p className="text-sm text-slate-500 mt-1 mb-5">{isRegister ? 'Register to start managing your knowledge base.' : 'Sign in to access your workspace and documents.'}</p>
            <form onSubmit={submitAuth} className="space-y-4">
              {isRegister && <label className="block text-sm text-slate-700">Full name
                <input required maxLength={255} autoComplete="name" value={fullName} onChange={event => setFullName(event.target.value)} className="input mt-1" />
              </label>}
              <label className="block text-sm text-slate-700">Email
                <input required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} className="input mt-1" />
              </label>
              <label className="block text-sm text-slate-700">Password
                <input required minLength={8} maxLength={72} type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} value={password} onChange={event => setPassword(event.target.value)} className="input mt-1" />
              </label>
              {formError && <p role="alert" className="text-sm text-red-600">{formError}</p>}
              <button disabled={busy} className="btn-md btn-primary w-full justify-center">{busy ? 'Please wait…' : isRegister ? 'Register' : 'Sign in'}</button>
            </form>
            <button onClick={() => { setIsRegister(value => !value); setFormError(''); }} className="mt-5 text-sm text-indigo-600 hover:text-indigo-700">
              {isRegister ? 'Already registered? Sign in' : 'New here? Create an account'}
            </button>
          </>
        )}
      </section>
    </main>
  );
}
