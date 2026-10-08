import { createClient } from "@supabase/supabase-js";
import { Database } from "../types/database.types";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  "https://braijzgcqyimvpoifwjg.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJyYWlqemdjcXlpbXZwb2lmd2pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA2MDUwMDMsImV4cCI6MjEwNjE4MTAwM30.Dy10C-173RfrJ2RkGtMkqUZgEABmkkgtunwMQ4LSVpQ";

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storage: typeof window !== "undefined" ? window.localStorage : undefined,
  },
});
