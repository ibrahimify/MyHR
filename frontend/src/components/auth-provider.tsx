"use client";

import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getSupabaseBrowserClient,
  supabaseConfigurationError,
  usesSupabaseAuth,
} from "@/lib/supabase";

type AuthState = {
  ready: boolean;
  user: User | null;
  configurationError: string;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(
    !usesSupabaseAuth || Boolean(supabaseConfigurationError),
  );
  const [user, setUser] = useState<User | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (supabaseConfigurationError) return;
    const client = getSupabaseBrowserClient();
    if (!client) return;
    let active = true;
    void client.auth.getSession().then(({ data }) => {
      if (!active) return;
      setUser(data.session?.user ?? null);
      setReady(true);
    });
    const { data } = client.auth.onAuthStateChange(
      (_event: AuthChangeEvent, session: Session | null) => {
        setUser(session?.user ?? null);
        setReady(true);
      },
    );
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!ready || !usesSupabaseAuth) return;
    if (!user && pathname !== "/login") router.replace("/login");
    if (user && pathname === "/login") router.replace("/");
  }, [pathname, ready, router, user]);

  const value = useMemo<AuthState>(
    () => ({
      ready,
      user,
      configurationError: supabaseConfigurationError,
      signOut: async () => {
        const client = getSupabaseBrowserClient();
        if (client) await client.auth.signOut();
      },
    }),
    [ready, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { configurationError, ready, user } = useAuth();
  if (configurationError) {
    return (
      <main className="auth-loading" role="alert">
        {configurationError}
      </main>
    );
  }
  if (!ready || (usesSupabaseAuth && !user)) {
    return (
      <main className="auth-loading" aria-busy="true">
        Loading your workspace
      </main>
    );
  }
  return children;
}
