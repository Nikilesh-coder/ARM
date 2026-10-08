import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { Database } from "../types/database.types";

function normalizeUrl(url?: string): string {
  if (!url) return "";
  let cleaned = url.trim().replace(/^["']+|["']+$/g, "").trim();
  if (cleaned && !cleaned.startsWith("http://") && !cleaned.startsWith("https://")) {
    cleaned = `https://${cleaned}`;
  }
  return cleaned;
}

function normalizeKey(key?: string): string {
  if (!key) return "";
  return key.trim().replace(/^["']+|["']+$/g, "").trim();
}

let clientInstance: SupabaseClient<Database> | null = null;

export function getSupabase(): SupabaseClient<Database> {
  if (clientInstance) {
    return clientInstance;
  }

  const supabaseUrl = normalizeUrl(process.env.NEXT_PUBLIC_SUPABASE_URL);
  const supabaseAnonKey = normalizeKey(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Supabase credentials missing: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be provided."
    );
  }

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
