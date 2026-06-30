import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { auth, googleProvider, isFirebaseConfigured } from "@/lib/firebase";
import { signInWithPopup, signOut as firebaseSignOut, onAuthStateChanged } from "firebase/auth";

export interface AppUser {
  uid: string;
  displayName: string;
  email: string;
  photoURL: string | null;
}

interface AuthCtx {
  user: AppUser | null;
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
  signInMock?: () => void;
  signInGooglePopup?: () => Promise<any>;
  isFirebaseConfigured: boolean;
}

const Ctx = createContext<AuthCtx>({
  user: null,
  session: null,
  loading: true,
  signOut: async () => {},
  isFirebaseConfigured: false,
});

function toAppUser(u: User | null | undefined): AppUser | null {
  if (!u) return null;
  const meta = (u.user_metadata ?? {}) as Record<string, string | undefined>;
  return {
    uid: u.id,
    displayName: meta.full_name ?? meta.name ?? (u.email ? u.email.split("@")[0] : "User"),
    email: u.email ?? "",
    photoURL: meta.avatar_url ?? meta.picture ?? null,
  };
}

const makeSessionFromFirebaseUser = (firebaseUser: any) => {
  return {
    access_token: firebaseUser.accessToken || "firebase-token",
    token_type: "bearer",
    expires_in: 3600,
    refresh_token: "firebase-refresh",
    user: {
      id: firebaseUser.uid,
      aud: "authenticated",
      role: "authenticated",
      email: firebaseUser.email || "",
      email_confirmed_at: new Date().toISOString(),
      user_metadata: {
        full_name: firebaseUser.displayName || "",
        avatar_url: firebaseUser.photoURL || `https://api.dicebear.com/7.x/adventurer/svg?seed=${firebaseUser.uid}`,
      },
    },
  } as any;
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const active = localStorage.getItem("tr:activeSession");
      if (active) {
        try {
          setSession(JSON.parse(active));
          setLoading(false);
          return;
        } catch {}
      }
    }

    if (isFirebaseConfigured) {
      const unsubFirebase = onAuthStateChanged(auth, (firebaseUser) => {
        if (firebaseUser) {
          setSession(makeSessionFromFirebaseUser(firebaseUser));
        } else {
          setSession(null);
        }
        setLoading(false);
      });
      return () => unsubFirebase();
    } else {
      const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
        setSession(s);
        setLoading(false);
      });
      supabase.auth.getSession().then(({ data }) => {
        setSession(data.session);
        setLoading(false);
      });
      return () => sub.subscription.unsubscribe();
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (session) {
        localStorage.setItem("tr:activeSession", JSON.stringify(session));
      } else {
        localStorage.removeItem("tr:activeSession");
      }
    }
  }, [session]);

  const signOut = async () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("tr:activeSession");
      localStorage.removeItem("tr:mockSession");
    }
    if (isFirebaseConfigured) {
      await firebaseSignOut(auth);
    } else {
      await supabase.auth.signOut();
    }
    setSession(null);
  };

  const signInMock = () => {
    const mockSession = {
      access_token: "mock-token",
      token_type: "bearer",
      expires_in: 3600,
      refresh_token: "mock-refresh",
      user: {
        id: "mock-user-id",
        aud: "authenticated",
        role: "authenticated",
        email: "recruiter@talentrank.ai",
        email_confirmed_at: new Date().toISOString(),
        user_metadata: {
          full_name: "Demo Recruiter",
          avatar_url: "https://api.dicebear.com/7.x/adventurer/svg?seed=demo",
        },
      },
    } as any;
    if (typeof window !== "undefined") {
      localStorage.setItem("tr:mockSession", JSON.stringify(mockSession));
      localStorage.setItem("tr:activeSession", JSON.stringify(mockSession));
    }
    setSession(mockSession);
  };

  const signInGooglePopup = async () => {
    if (!isFirebaseConfigured) {
      throw new Error("Firebase configuration env variables are missing.");
    }
    const result = await signInWithPopup(auth, googleProvider);
    if (result.user) {
      const mockSess = makeSessionFromFirebaseUser(result.user);
      if (typeof window !== "undefined") {
        localStorage.setItem("tr:activeSession", JSON.stringify(mockSess));
      }
      setSession(mockSess);
    }
    return result;
  };

  return (
    <Ctx.Provider value={{ session, user: toAppUser(session?.user), loading, signOut, signInMock, signInGooglePopup, isFirebaseConfigured }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
