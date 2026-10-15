/**
 * frontend/src/pages/LandingPage.tsx
 * ────────────────────────────────────
 * Foundation-phase landing page.
 *
 * Shows:
 *  - Application title & tagline
 *  - Live API health status (calls GET /api/v1/health)
 *  - Tech stack badge grid
 *  - Placeholder "Coming Soon" feature cards
 *
 * All API calls will be centralised in src/api/ in future phases.
 */

import { useEffect, useState } from "react";
import { API_BASE_URL, apiUrl } from "../api/client";

// ── Types ────────────────────────────────────────────────────────────────────
interface HealthData {
  status: string;
  app_name: string;
  version: string;
  environment: string;
}

type ApiState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "success"; data: HealthData }
  | { phase: "error"; message: string };

// ── Constants ────────────────────────────────────────────────────────────────
const STACK_BADGES = [
  { label: "FastAPI",       color: "from-teal-500 to-emerald-600",   icon: "⚡" },
  { label: "PostgreSQL",    color: "from-blue-500 to-blue-700",       icon: "🐘" },
  { label: "pgvector",      color: "from-violet-500 to-purple-700",   icon: "🔢" },
  { label: "SQLAlchemy",    color: "from-red-500 to-rose-700",        icon: "🗄️" },
  { label: "Alembic",       color: "from-amber-500 to-orange-600",    icon: "🔄" },
  { label: "React 18",      color: "from-cyan-400 to-sky-600",        icon: "⚛️" },
  { label: "Vite 5",        color: "from-yellow-400 to-amber-500",    icon: "🚀" },
  { label: "Tailwind CSS",  color: "from-sky-400 to-cyan-600",        icon: "🎨" },
  { label: "Groq",          color: "from-orange-400 to-red-500",      icon: "🦙" },
  { label: "Gemini",        color: "from-blue-400 to-indigo-600",     icon: "✨" },
];

const UPCOMING_FEATURES = [
  {
    icon: "🔐",
    title: "Authentication & RBAC",
    desc: "JWT-based auth with role-based access control for enterprise users.",
    phase: "Phase 2",
  },
  {
    icon: "📄",
    title: "Document Processing",
    desc: "Upload PDFs, DOCX, and web pages. Auto-parse and chunk for retrieval.",
    phase: "Phase 3",
  },
  {
    icon: "🧠",
    title: "RAG Query Engine",
    desc: "Semantic search over your knowledge base powered by pgvector embeddings.",
    phase: "Phase 4",
  },
  {
    icon: "🤖",
    title: "AI Answer Generation",
    desc: "LLM-powered answers grounded in your organisation's documents.",
    phase: "Phase 5",
  },
];

// ── Component ─────────────────────────────────────────────────────────────────
export default function LandingPage() {
  const [apiState, setApiState] = useState<ApiState>({ phase: "idle" });

  // Poll the health endpoint once on mount
  useEffect(() => {
    setApiState({ phase: "loading" });

    fetch(apiUrl("/health"))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HealthData>;
      })
      .then((data) => setApiState({ phase: "success", data }))
      .catch((_err: Error) =>
        setApiState({
          phase: "error",
          message:
            "Cannot reach backend. Start the server with: uvicorn app.main:app --reload",
        })
      );
  }, []);

  return (
    <div className="min-h-screen px-4 py-16 md:py-24">
      {/* ── Background decorations ────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-brand-600/20 blur-[120px] animate-pulse-slow" />
        <div className="absolute top-1/3 -right-40 h-80 w-80 rounded-full bg-accent-400/10 blur-[100px] animate-pulse-slow" />
        <div className="absolute bottom-0 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-brand-800/20 blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-5xl space-y-16">
        {/* ── Hero ──────────────────────────────────────────── */}
        <header className="text-center space-y-6 animate-fade-in">
          {/* Phase badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-500/40 bg-brand-500/10 px-4 py-1.5 text-sm text-brand-300">
            <span className="h-2 w-2 rounded-full bg-brand-400 animate-pulse" />
            Foundation Phase — v0.1.0
          </div>

          {/* Title */}
          <h1 className="text-4xl font-extrabold tracking-tight md:text-6xl text-shadow-glow">
            <span className="gradient-text">AI Knowledge Hub</span>
          </h1>

          {/* Subtitle */}
          <p className="mx-auto max-w-2xl text-lg text-slate-400 leading-relaxed">
            An enterprise-grade{" "}
            <span className="text-brand-400 font-semibold">
              RAG Query Resolution Platform
            </span>{" "}
            built as a B.Tech final-year project. Powered by FastAPI, pgvector,
            and React.
          </p>
        </header>

        {/* ── API Health Status ─────────────────────────────── */}
        <section aria-label="API health status" className="animate-slide-up">
          <div className="glass-card p-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-1">
                  Backend API Status
                </h2>
                {apiState.phase === "loading" && (
                  <p className="text-slate-300 flex items-center gap-2">
                    <span className="inline-block h-3 w-3 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
                    Connecting to{" "}
                    <code className="font-mono text-brand-300 text-sm">
                      {API_BASE_URL}
                    </code>
                    …
                  </p>
                )}
                {apiState.phase === "success" && (
                  <div className="space-y-1">
                    <p className="text-lg font-semibold text-white flex items-center gap-2">
                      <span className="status-badge-success">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Online
                      </span>
                      {apiState.data.app_name}
                    </p>
                    <p className="text-sm text-slate-400 font-mono">
                      v{apiState.data.version} · {apiState.data.environment}
                    </p>
                  </div>
                )}
                {apiState.phase === "error" && (
                  <div>
                    <span className="status-badge status-badge-pending">
                      ⚠ Offline
                    </span>
                    <p className="mt-2 text-sm text-amber-300 font-mono bg-amber-500/10 rounded-lg p-3 border border-amber-500/20">
                      {apiState.message}
                    </p>
                  </div>
                )}
              </div>

              <a
                href={`${API_BASE_URL}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                id="swagger-link"
                className="btn-ghost text-sm"
              >
                Open Swagger UI ↗
              </a>
            </div>
          </div>
        </section>

        {/* ── Tech Stack ────────────────────────────────────── */}
        <section aria-label="Technology stack">
          <h2 className="mb-6 text-center text-sm font-semibold uppercase tracking-widest text-slate-500">
            Technology Stack
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-4">
            {STACK_BADGES.map((tech) => (
              <div
                key={tech.label}
                className="glass-card flex items-center gap-3 p-4"
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${tech.color} text-lg shadow-lg`}
                >
                  {tech.icon}
                </span>
                <span className="text-sm font-medium text-slate-200">
                  {tech.label}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Upcoming Features ─────────────────────────────── */}
        <section aria-label="Upcoming features">
          <h2 className="mb-6 text-center text-sm font-semibold uppercase tracking-widest text-slate-500">
            Roadmap — Coming Soon
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {UPCOMING_FEATURES.map((feature) => (
              <div key={feature.title} className="glass-card p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{feature.icon}</span>
                    <h3 className="font-semibold text-slate-100">
                      {feature.title}
                    </h3>
                  </div>
                  <span className="status-badge status-badge-pending shrink-0">
                    {feature.phase}
                  </span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed pl-9">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Footer ────────────────────────────────────────── */}
        <footer className="text-center text-sm text-slate-600 space-y-1">
          <p>
            B.Tech Final Year Project ·{" "}
            <span className="gradient-text font-medium">AI Knowledge Hub</span>
          </p>
          <p>FastAPI · PostgreSQL · pgvector · React · Vite · Tailwind CSS</p>
        </footer>
      </div>
    </div>
  );
}
