// src/components/ui/Badge.tsx
import type { TicketStatus, TicketPriority, DocumentStatus, MemberRole } from '../../types';

type BadgeVariant = 'green' | 'blue' | 'amber' | 'red' | 'slate' | 'purple' | 'indigo';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  dot?: boolean;
}

export function Badge({ children, variant = 'slate', dot }: BadgeProps) {
  const cls = `badge badge-${variant}`;
  return (
    <span className={cls}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />}
      {children}
    </span>
  );
}

// ── Convenience mappers ────────────────────────────────────────
export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const map: Record<TicketStatus, { variant: BadgeVariant; label: string }> = {
    'open':        { variant: 'amber', label: 'Open' },
    'in-progress': { variant: 'blue',  label: 'In Progress' },
    'resolved':    { variant: 'green', label: 'Resolved' },
    'closed':      { variant: 'slate', label: 'Closed' },
  };
  const { variant, label } = map[status];
  return <Badge variant={variant} dot>{label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const map: Record<TicketPriority, { variant: BadgeVariant; label: string }> = {
    'low':      { variant: 'slate',  label: 'Low' },
    'medium':   { variant: 'blue',   label: 'Medium' },
    'high':     { variant: 'amber',  label: 'High' },
    'critical': { variant: 'red',    label: 'Critical' },
  };
  const { variant, label } = map[priority];
  return <Badge variant={variant}>{label}</Badge>;
}

export function DocStatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { variant: BadgeVariant; label: string }> = {
    'processed':  { variant: 'green', label: 'Processed' },
    'processing': { variant: 'blue',  label: 'Processing' },
    'failed':     { variant: 'red',   label: 'Failed' },
  };
  const { variant, label } = map[status];
  return <Badge variant={variant} dot>{label}</Badge>;
}

export function RoleBadge({ role }: { role: MemberRole }) {
  const map: Record<MemberRole, { variant: BadgeVariant }> = {
    'admin':  { variant: 'indigo' },
    'editor': { variant: 'purple' },
    'viewer': { variant: 'slate' },
  };
  return (
    <Badge variant={map[role].variant}>
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </Badge>
  );
}
