/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string
  readonly VITE_ANTHROPIC_MODEL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/**
 * The vite.config.ts exposes `process.env` via `define`, so we can read
 * `ANTHROPIC_MODEL` (set in .claude/settings.json) at build/dev time.
 */
declare namespace NodeJS {
  interface ProcessEnv {
    ANTHROPIC_MODEL?: string
  }
}

/**
 * The vite.config.ts exposes `process.env` via `define`, so `process` is
 * available at build time but not declared as a browser global.
 */
declare const process: {
  env: NodeJS.ProcessEnv
}
