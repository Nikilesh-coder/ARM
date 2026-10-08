import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { Database } from "../types/database.types";

const DEFAULT_SUPABASE_URL = "https://braijzgcqyimvpoifwjg.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyYWlqemdjcXlpbXZwb2lmd2pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA2MDUwMDMsImV4cCI6MjEwNjE4MTAwM30.Dy10C-173RfrJ2RkGtMkqUZgEABmkkgtunwMQ4LSVpQ";

function normalizeUrl(url?: string): string {
  if (!url) return DEFAULT_SUPABASE_URL;
  let cleaned = url.trim().replace(/^["']+|["']+$/g, "").trim();
  if (
    !cleaned ||
    cleaned.includes("YOUR_EXISTING_SUPABASE_URL") ||
    cleaned.includes("your-project.supabase.co") ||
    cleaned.toLowerCase() === "placeholder" ||
    cleaned.toLowerCase() === "undefined"
  ) {
    return DEFAULT_SUPABASE_URL;
  }
  if (!cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
    cleaned = `https://${cleaned}`;
  }
  return cleaned;
}

function normalizeKey(key?: string): string {
  if (!key) return DEFAULT_SUPABASE_ANON_KEY;
  let cleaned = key.trim().replace(/^["']+|["']+$/g, "").trim();
  if (
    !cleaned ||
    cleaned.includes("YOUR_EXISTING_SUPABASE_ANON_KEY") ||
    cleaned.includes("your-anon-public-key") ||
    cleaned.toLowerCase() === "placeholder" ||
    cleaned.toLowerCase() === "undefined"
  ) {
    return DEFAULT_SUPABASE_ANON_KEY;
  }
  return cleaned;
}

let clientInstance: SupabaseClient<Database> | null = null;

export function getSupabase(): SupabaseClient<Database> {
  if (clientInstance) {
    return clientInstance;
  }

  const supabaseUrl = normalizeUrl(process.env.NEXT_PUBLIC_SUPABASE_URL);
  const supabaseAnonKey = normalizeKey(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

  clientInstance = createClient<Database>(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storage: typeof window !== "undefined" ? window.localStorage : undefined,
    },
  });

  return clientInstance;
}

export const supabase = new Proxy({} as SupabaseClient<Database>, {
  get(_target, prop) {
    const client = getSupabase();
    const val = (client as any)[prop];
    if (typeof val === "function") {
      return val.bind(client);
    }
    return val;
  },
});
