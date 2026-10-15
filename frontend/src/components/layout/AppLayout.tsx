// src/components/layout/AppLayout.tsx
import { useState, lazy, Suspense } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import type { NavPage } from '../../types';
import AuthGate from '../../auth/AuthGate';
import { useAuth } from '../../auth/AuthContext';

// Lazy-load pages to keep initial bundle small
const OverviewPage       = lazy(() => import('../../pages/OverviewPage'));
const AIChatPage         = lazy(() => import('../../pages/AIChatPage'));
const DocumentsPage      = lazy(() => import('../../pages/DocumentsPage'));
const ConversationsPage  = lazy(() => import('../../pages/ConversationsPage'));
const SupportTicketsPage = lazy(() => import('../../pages/SupportTicketsPage'));
const TeamPage           = lazy(() => import('../../pages/TeamPage'));
const SettingsPage       = lazy(() => import('../../pages/SettingsPage'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-500">Loading…</span>
      </div>
    </div>
  );
}

function PageRenderer({ page }: { page: NavPage }) {
  switch (page) {
    case 'overview':        return <OverviewPage />;
    case 'ai-chat':         return <AIChatPage />;
    case 'documents':       return <DocumentsPage />;
    case 'conversations':   return <ConversationsPage />;
    case 'support-tickets': return <SupportTicketsPage />;
    case 'team':            return <TeamPage />;
    case 'settings':        return <SettingsPage />;
  }
}

export default function AppLayout() {
  const { error, workspace } = useAuth();
  const [currentPage, setCurrentPage]       = useState<NavPage>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return <AuthGate>
    {error && <div role="alert" className="fixed top-2 right-2 z-50 rounded-lg bg-red-50 text-red-700 border border-red-200 px-4 py-2 text-sm">{error}</div>}
    {workspace && (
    <div className="min-h-screen bg-slate-50">
      <Sidebar
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main content offset by sidebar width on desktop */}
      <div className={`
        flex flex-col min-h-screen transition-all duration-300
        ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-60'}
      `}>
        <Header
          currentPage={currentPage}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          <Suspense fallback={<PageLoader />}>
            <PageRenderer key={`${currentPage}-${workspace?.id}`} page={currentPage} />
          </Suspense>
        </main>
      </div>
    </div>
    )}
  </AuthGate>;
}
