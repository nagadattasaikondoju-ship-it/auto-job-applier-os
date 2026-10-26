"use client";

import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  updateProfile,
} from "firebase/auth";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setTokenGetter } from "@/lib/api/client";
import { getFirebaseAuth, isFirebaseConfigured } from "@/lib/firebase";

export interface AppUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  isDevUser: boolean;
}

interface AuthContextValue {
  user: AppUser | null;
  loading: boolean;
  firebaseEnabled: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (name: string, email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signInAsDevUser: (uid: string) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Dev login only works against a backend with APP_ENV=development, which accepts `dev-token-<uid>`.
const DEV_USER_KEY = "applyon.devUser";

function readDevUser(): AppUser | null {
  try {
    const uid = window.localStorage.getItem(DEV_USER_KEY);
    if (!uid) return null;
    return { uid, email: `${uid}@example.com`, displayName: "Dev User", photoURL: null, isDevUser: true };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) {
      let cancelled = false;
      void Promise.resolve().then(() => {
        if (cancelled) return;
        setUser(readDevUser());
        setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }
    return onAuthStateChanged(auth, (fbUser) => {
      setUser(
        fbUser
          ? {
              uid: fbUser.uid,
              email: fbUser.email,
              displayName: fbUser.displayName,
              photoURL: fbUser.photoURL,
              isDevUser: false,
            }
          : readDevUser()
      );
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    setTokenGetter(async () => {
      const auth = getFirebaseAuth();
      if (auth?.currentUser) return auth.currentUser.getIdToken();
      const dev = readDevUser();
      return dev ? `dev-token-${dev.uid}` : null;
    });
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error("Firebase is not configured.");
    await signInWithPopup(auth, new GoogleAuthProvider());
  }, []);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error("Firebase is not configured.");
    await signInWithEmailAndPassword(auth, email, password);
  }, []);

  const signUpWithEmail = useCallback(async (name: string, email: string, password: string) => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error("Firebase is not configured.");
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    if (name) await updateProfile(cred.user, { displayName: name });
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error("Firebase is not configured.");
    await sendPasswordResetEmail(auth, email);
  }, []);

  const signInAsDevUser = useCallback((uid: string) => {
    try {
      window.localStorage.setItem(DEV_USER_KEY, uid);
    } catch {
      // storage unavailable: the session still works until reload
    }
    setUser({ uid, email: `${uid}@example.com`, displayName: "Dev User", photoURL: null, isDevUser: true });
  }, []);

  const signOut = useCallback(async () => {
    try {
      window.localStorage.removeItem(DEV_USER_KEY);
    } catch {
      // ignore
    }
    const auth = getFirebaseAuth();
    if (auth) await firebaseSignOut(auth);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      firebaseEnabled: isFirebaseConfigured,
      signInWithGoogle,
      signInWithEmail,
      signUpWithEmail,
      resetPassword,
      signInAsDevUser,
      signOut,
    }),
    [user, loading, signInWithGoogle, signInWithEmail, signUpWithEmail, resetPassword, signInAsDevUser, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Turn Firebase auth error codes into messages a person can act on. */
export function authErrorMessage(err: unknown): string {
  const code = (err as { code?: string })?.code ?? "";
  const map: Record<string, string> = {
    "auth/invalid-credential": "That email and password don't match.",
    "auth/user-not-found": "No account found with that email.",
    "auth/wrong-password": "That email and password don't match.",
    "auth/email-already-in-use": "An account with this email already exists. Try logging in.",
    "auth/weak-password": "Use a password with at least 6 characters.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/popup-closed-by-user": "The Google sign-in window was closed.",
    "auth/too-many-requests": "Too many attempts. Wait a minute and try again.",
  };
  return map[code] ?? (err instanceof Error ? err.message : "Something went wrong. Try again.");
}
