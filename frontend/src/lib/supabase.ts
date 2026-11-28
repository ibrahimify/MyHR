import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

export const usesSupabaseAuth =
  process.env.NEXT_PUBLIC_AUTH_MODE !== "local";

export const supabaseConfigurationError =
  usesSupabaseAuth &&
  (!process.env.NEXT_PUBLIC_SUPABASE_URL ||
    !process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)
    ? "Supabase authentication is not configured."
    : "";

let browserClient: SupabaseClient | undefined;

export function getSupabaseBrowserClient() {
  if (!usesSupabaseAuth) return null;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) {
    throw new Error("Supabase authentication is not configured.");
  }
  browserClient ??= createBrowserClient(url, publishableKey);
  return browserClient;
}

export async function getAccessToken() {
  const client = getSupabaseBrowserClient();
  if (!client) return null;
  const { data, error } = await client.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}
