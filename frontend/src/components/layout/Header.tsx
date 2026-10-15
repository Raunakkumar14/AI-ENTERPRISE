import { Menu } from 'lucide-react';
import type { NavPage } from '../../types';
import { useAuth } from '../../auth/AuthContext';

const PAGE_META: Record<NavPage, { title: string; description: string }> = {
  overview: { title: 'Overview', description: 'Workspace activity from your database' },
  'ai-chat': { title: 'AI Chat', description: 'Ask questions about your knowledge base' },
  documents: { title: 'Documents', description: 'Manage and preview extracted document content' },
  conversations: { title: 'Conversations', description: 'Browse your persisted AI conversation history' },
  'support-tickets': { title: 'Support Tickets', description: 'Ticket management is not available in this backend yet' },
  team: { title: 'Team', description: 'Manage workspace members and permissions' },
  settings: { title: 'Settings', description: 'Configure workspace details' },
};

interface HeaderProps {
  currentPage: NavPage;
  onOpenMobileSidebar: () => void;
}

export default function Header({ currentPage, onOpenMobileSidebar }: HeaderProps) {
  const { title, description } = PAGE_META[currentPage];
  const { workspace } = useAuth();
  return (
    <header className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-slate-200 min-h-14 flex items-center px-4 gap-3 flex-shrink-0">
      <button onClick={onOpenMobileSidebar} className="lg:hidden btn-ghost btn-sm p-1.5" aria-label="Open menu">
        <Menu size={18} />
      </button>
      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-slate-900 leading-tight">{title}</h1>
        <p className="text-xs text-slate-500 hidden sm:block">{workspace?.name} · {description}</p>
      </div>
    </header>
  );
}
