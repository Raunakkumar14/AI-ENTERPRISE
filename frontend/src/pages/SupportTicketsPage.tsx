import { LifeBuoy } from 'lucide-react';

export default function SupportTicketsPage() {
  return (
    <section className="max-w-3xl mx-auto card p-8 text-center">
      <div className="w-12 h-12 mx-auto rounded-xl bg-amber-100 text-amber-700 grid place-items-center"><LifeBuoy size={22} /></div>
      <h2 className="text-lg font-semibold text-slate-900 mt-4">Support tickets are not connected</h2>
      <p className="text-sm text-slate-600 mt-2">The current FastAPI backend has no ticket model or ticket endpoints, so no ticket records or actions are shown here. This page will be available after a ticket backend is implemented.</p>
    </section>
  );
}
