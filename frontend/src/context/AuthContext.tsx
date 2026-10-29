import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

import { ApiError } from "../lib/api";
import { authService } from "../lib/auth";
import type {
  AuthUser,
  GoogleLoginInput,
  LoginInput,
  RegisterInput,
} from "../lib/auth";

type AuthStatus = "loading" | "authenticated" | "anonymous" | "error";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
  login: (input: LoginInput) => Promise<AuthUser>;
  googleLogin: (input: GoogleLoginInput) => Promise<AuthUser>;
  register: (input: RegisterInput) => Promise<string>;
  logout: () => Promise<void>;
  updateUser: (user: AuthUser) => void;
  retrySession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionRequestRef = useRef(0);

  const retrySession = useCallback(async () => {
    const requestId = ++sessionRequestRef.current;
    setStatus("loading");
    setError(null);
    try {
      const currentUser = await authService.getCurrentUser();
      if (requestId !== sessionRequestRef.current) return;
      setUser(currentUser);
      setStatus("authenticated");
    } catch (requestError) {
      if (requestId !== sessionRequestRef.current) return;
      if (requestError instanceof ApiError && requestError.status === 401) {
        setUser(null);
        setStatus("anonymous");
        return;
      }
      setUser(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "We could not check your sign-in session.",
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void retrySession();
  }, [retrySession]);

  const login = useCallback(async (input: LoginInput) => {
    const signedInUser = await authService.login(input);
    sessionRequestRef.current += 1;
    setUser(signedInUser);
    setError(null);
    setStatus("authenticated");
    return signedInUser;
  }, []);

  const googleLogin = useCallback(async (input: GoogleLoginInput) => {
    const signedInUser = await authService.googleLogin(input);
    sessionRequestRef.current += 1;
    setUser(signedInUser);
    setError(null);
    setStatus("authenticated");
    return signedInUser;
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const result = await authService.register(input);
    return result.message;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    sessionRequestRef.current += 1;
    setUser(null);
    setError(null);
    setStatus("anonymous");
  }, []);

  const updateUser = useCallback((updatedUser: AuthUser) => {
    setUser(updatedUser);
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      error,
      login,
      googleLogin,
      register,
      logout,
      updateUser,
      retrySession,
    }),
    [
      status,
      user,
      error,
      login,
      googleLogin,
      register,
      logout,
      updateUser,
      retrySession,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
