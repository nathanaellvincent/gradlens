import { SearchConsole } from "@/components/search-console";

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-16 sm:py-24">
      <header className="mb-12">
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-[color:var(--color-accent)]">
          GradLens · v0.1
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
          Semantic search for graduate schemes.
        </h1>
        <p className="mt-4 max-w-xl text-[color:var(--color-ink-muted)] leading-relaxed">
          Describe the role you want in plain English. No keyword-matching
          boards, no paywalled aggregators — just local embeddings over a
          curated set of open engineering & research roles.
        </p>
      </header>

      <SearchConsole />

      <footer className="mt-24 border-t border-[color:var(--color-border)] pt-6 font-mono text-[10px] uppercase tracking-[0.2em] text-[color:var(--color-ink-dim)]">
        <p>
          Built by{" "}
          <a
            href="https://github.com/nathanaellvincent"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[color:var(--color-ink-muted)] hover:text-[color:var(--color-accent-soft)]"
          >
            Vincent Nathanael
          </a>
          {" · "}
          <a
            href="https://github.com/nathanaellvincent/gradlens"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[color:var(--color-ink-muted)] hover:text-[color:var(--color-accent-soft)]"
          >
            source
          </a>
          {" · "}
          local embeddings, zero API cost
        </p>
      </footer>
    </main>
  );
}
