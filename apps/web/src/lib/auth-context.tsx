"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, Session } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  userName: string;
  userEmail: string;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<Session | null>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  isLoading: true,
  isAuthenticated: false,
  userName: "",
  userEmail: "",
  signOut: async () => {},
  refreshSession: async () => null,
});

function resolveUserName(user: User | null): string {
  if (!user) return "";
  const metaName = user.user_metadata?.full_name || user.user_metadata?.name;
  if (metaName && typeof metaName === "string" && metaName.trim()) {
    return metaName.trim();
  }
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("arm_user_name");
    if (stored && stored.trim()) return stored.trim();
  }
  if (user.email) {
    const prefix = user.email.split("@")[0].replace(/[._-]/g, " ");
    return prefix.charAt(0).toUpperCase() + prefix.slice(1);
  }
  return "Scholar";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [userName, setUserName] = useState<string>("");
  const [userEmail, setUserEmail] = useState<string>("");

  const syncUserState = useCallback((currentSession: Session | null) => {
    setSession(currentSession);
    const currentUser = currentSession?.user ?? null;
    setUser(currentUser);

    if (currentUser) {
      const name = resolveUserName(currentUser);
      const email = currentUser.email || "";
      setUserName(name);
      setUserEmail(email);

      if (typeof window !== "undefined") {
        if (name) localStorage.setItem("arm_user_name", name);
        if (email) localStorage.setItem("arm_user_email", email);
        if (currentUser.id) localStorage.setItem("arm_user_id", currentUser.id);
      }
    } else {
      setUserName("");
      setUserEmail("");
    }
  }, []);

  // Initialize and restore session on startup
  useEffect(() => {
    let mounted = true;

    async function restoreSession() {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          console.warn("[Auth] Error restoring session:", error.message);
        }

        if (mounted) {
          const currentSession = data?.session ?? null;
          syncUserState(currentSession);
          setIsLoading(false);
        }
      } catch (err) {
        console.error("[Auth] Unexpected error during session restore:", err);
        if (mounted) {
          setSession(null);
          setUser(null);
          setIsLoading(false);
        }
      }
    }

    restoreSession();

    // Listen for auth state changes across tabs and within the app
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, newSession) => {
      if (!mounted) return;

      if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "USER_UPDATED") {
        syncUserState(newSession);
        setIsLoading(false);
      } else if (event === "SIGNED_OUT") {
        setSession(null);
        setUser(null);
        setUserName("");
        setUserEmail("");
        if (typeof window !== "undefined") {
          localStorage.removeItem("arm_user_name");
          localStorage.removeItem("arm_user_email");
          localStorage.removeItem("arm_user_id");
          localStorage.removeItem("arm_active_project");
        }
        setIsLoading(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [syncUserState]);

  const signOut = useCallback(async () => {
    try {
      setIsLoading(true);
      await supabase.auth.signOut();
    } catch (err) {
      console.error("[Auth] Error signing out:", err);
    } finally {
      setSession(null);
      setUser(null);
      setUserName("");
      setUserEmail("");
      if (typeof window !== "undefined") {
        localStorage.removeItem("arm_user_name");
        localStorage.removeItem("arm_user_email");
        localStorage.removeItem("arm_user_id");
        localStorage.removeItem("arm_active_project");
      }
      setIsLoading(false);
      router.replace("/login");
    }
  }, [router]);

  const refreshSession = useCallback(async () => {
    try {
      const { data, error } = await supabase.auth.refreshSession();
      if (error) throw error;
      syncUserState(data.session);
      return data.session;
    } catch (err) {
      console.warn("[Auth] Failed to refresh session:", err);
      return null;
    }
  }, [syncUserState]);

  const value = {
    user,
    session,
    isLoading,
    isAuthenticated: !!session && !!user,
    userName,
    userEmail,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
