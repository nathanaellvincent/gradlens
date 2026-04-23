"use client";

/**
 * Search console — the single interactive surface for GradLens MVP.
 *
 * State machine:
 *   idle     → nothing submitted yet; show suggested queries
 *   loading  → request in flight; disable form, show spinner
 *   ok       → got results (may be empty list); render cards
 *   error    → request failed; show message + retry affordance
 *
 * In-flight requests are cancelled on resubmit via AbortController so a
 * slow first query never clobbers a faster second one.
 */

import { useRef, useState } from "react";
import { search, type SearchResponse } from "@/lib/api";

type State =
  | { kind: "idle" }
  | { kind: "loading"; query: string }
  | { kind: "ok"; data: SearchResponse }
  | { kind: "error"; query: string; message: string };

const SUGGESTIONS = [
  "new grad software engineer, remote UK",
  "machine learning internship, PhD",
  "backend engineer at a fintech",
  "AI research scientist, London",
  "frontend engineer new grad",
];

export function SearchConsole() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  async function runSearch(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ kind: "loading", query: trimmed });
    try {
      const data = await search(trimmed, 10, ctrl.signal);
      if (ctrl.signal.aborted) return;
      setState({ kind: "ok", data });
    } catch (err) {
      if (ctrl.signal.aborted) return;
      const message = err instanceof Error ? err.message : String(err);
      setState({ kind: "error", query: trimmed, message });
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
        className="flex flex-col gap-3"
      >
        <label
          htmlFor="query"
          className="font-mono text-[11px] uppercase tracking-[0.2em] text-[color:var(--color-accent)]"
        >
          Describe the role you want
        </label>
        <div className="flex gap-2">
          <input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. new grad machine learning engineer, remote UK"
            autoFocus
            disabled={state.kind === "loading"}
            className="flex-1 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3 text-[color:var(--color-ink)] placeholder:text-[color:var(--color-ink-dim)] outline-none transition focus:border-[color:var(--color-accent)] disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={state.kind === "loading" || !query.trim()}
            className="rounded-md border border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10 px-5 py-3 text-sm font-medium text-[color:var(--color-accent-soft)] transition hover:bg-[color:var(--color-accent)]/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {state.kind === "loading" ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {state.kind === "idle" && (
        <Suggestions
          onPick={(s) => {
            setQuery(s);
            void runSearch(s);
          }}
        />
      )}

      {state.kind === "loading" && <LoadingBar query={state.query} />}

      {state.kind === "error" && (
        <ErrorPanel
          message={state.message}
          onRetry={() => runSearch(state.query)}
        />
      )}

      {state.kind === "ok" && <Results data={state.data} />}
    </div>
  );
}

function Suggestions({ onPick }: { onPick: (s: string) => void }) {
  return (
    <section>
      <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-[color:var(--color-ink-dim)]">
        Try one of these
      </p>
      <ul className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <li key={s}>
            <button
              type="button"
              onClick={() => onPick(s)}
              className="rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-bg-soft)] px-3 py-1.5 text-sm text-[color:var(--color-ink-muted)] transition hover:border-[color:var(--color-accent)]/40 hover:text-[color:var(--color-ink)]"
            >
              {s}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function LoadingBar({ query }: { query: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-[color:var(--color-ink-muted)]">
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[color:var(--color-accent)]" />
      <span>
        Embedding <span className="text-[color:var(--color-ink)]">{`"${query}"`}</span>{" "}
        and searching the index…
      </span>
    </div>
  );
}

function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-md border border-red-900/70 bg-red-950/30 px-4 py-3 text-sm text-red-200">
      <p className="font-medium">Search failed</p>
      <p className="mt-1 font-mono text-xs text-red-300/80">{message}</p>
      <p className="mt-2 text-xs text-red-200/70">
        Is the API running on{" "}
        <code className="rounded bg-red-950 px-1 py-0.5">127.0.0.1:8000</code>?
        Start it with <code className="rounded bg-red-950 px-1 py-0.5">uv run gradlens-api</code>.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded border border-red-700 px-3 py-1 text-xs hover:bg-red-900/30"
      >
        Retry
      </button>
    </div>
  );
}

function Results({ data }: { data: SearchResponse }) {
  return (
    <section>
      <div className="mb-4 flex items-baseline justify-between font-mono text-[11px] text-[color:var(--color-ink-dim)]">
        <span>
          {data.total} hit{data.total === 1 ? "" : "s"} from {data.index_size.toLocaleString()}{" "}
          indexed roles
        </span>
        <span>{data.latency_ms.toFixed(1)} ms</span>
      </div>

      {data.hits.length === 0 ? (
        <p className="rounded border border-[color:var(--color-border)] bg-[color:var(--color-bg-soft)] px-4 py-8 text-center text-sm text-[color:var(--color-ink-muted)]">
          No matches. Try a broader query, or ingest more company boards
          with <code className="rounded bg-[color:var(--color-surface)] px-1 py-0.5">gradlens-ingest</code>.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {data.hits.map((hit) => (
            <li key={`${hit.source}-${hit.company}-${hit.upstream_id}`}>
              <a
                href={hit.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-soft)] px-5 py-4 transition hover:border-[color:var(--color-accent)]/40 hover:bg-[color:var(--color-surface)]"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-base font-semibold text-[color:var(--color-ink)] group-hover:text-[color:var(--color-accent-soft)]">
                    {hit.title.trim()}
                  </h3>
                  <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.15em] text-[color:var(--color-ink-dim)]">
                    d={hit.distance.toFixed(3)}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-[color:var(--color-ink-muted)]">
                  <span className="text-[color:var(--color-accent)]">
                    {hit.company}
                  </span>
                  {hit.location && (
                    <>
                      <span aria-hidden>·</span>
                      <span>{hit.location}</span>
                    </>
                  )}
                </div>
                <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-[color:var(--color-ink-muted)]">
                  {hit.snippet}
                </p>
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
