"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  login as apiLogin,
  loginWithGoogle as apiLoginWithGoogle,
  getUserProfile,
  logout as apiLogout,
} from "@/services/api";
import { UserProfile } from "@/types/user";
import { ROUTES } from "@/routes/routePaths";
import {
  clearAuthCookies,
  updateAuthCookies,
  syncAuthState,
  subscribeToAuthChanges,
} from "@/utils/authSync";

const USER_CACHE_KEY = "auth_user_cache_v1";
const USER_CACHE_TTL_MS = 6 * 60 * 60 * 1000;

type CachedUserPayload = {
  user: UserProfile;
  token: string;
  cachedAt: number;
};

const readCachedUser = (): CachedUserPayload | null => {
  try {
    const raw = sessionStorage.getItem(USER_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CachedUserPayload;
    if (!parsed?.user || !parsed?.token || !parsed?.cachedAt) return null;
    return parsed;
  } catch {
    return null;
  }
};

const writeCachedUser = (user: UserProfile, token: string) => {
  const payload: CachedUserPayload = {
    user,
    token,
    cachedAt: Date.now(),
  };
  sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(payload));
};

const clearCachedUser = () => {
  sessionStorage.removeItem(USER_CACHE_KEY);
};

type AuthContextValue = {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (username_or_email: string, password: string) => Promise<UserProfile | null>;
  loginWithGoogle: (googleToken: string, tipo: string) => Promise<UserProfile | null>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<UserProfile | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function useProvideAuth(): AuthContextValue {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const userRef = useRef<UserProfile | null>(null);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  const clearSession = useCallback(() => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    clearCachedUser();
    clearAuthCookies();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const checkStorageAuth = useCallback(() => {
    const token = sessionStorage.getItem("access_token");
    const authenticated = !!token;
    setIsAuthenticated(authenticated);
    return authenticated;
  }, []);

  const fetchUserProfile = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const token = sessionStorage.getItem("access_token");
      if (!token) {
        setUser(null);
        setIsAuthenticated(false);
        return null;
      }

      const userProfile = await getUserProfile();
      setUser(userProfile);
      setIsAuthenticated(true);
      writeCachedUser(userProfile, token);
      syncAuthState();
      return userProfile;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        clearSession();
        return null;
      }

      return userRef.current;
    } finally {
      setLoading(false);
    }
  }, [clearSession]);

  const login = useCallback(
    async (username_or_email: string, password: string): Promise<UserProfile | null> => {
      try {
        setLoading(true);
        setError(null);

        const loginData = await apiLogin(username_or_email, password);
        const { access, refresh } = loginData;

        sessionStorage.setItem("access_token", access);
        sessionStorage.setItem("refresh_token", refresh);
        updateAuthCookies(access);

        setIsAuthenticated(true);
        return await fetchUserProfile();
      } catch (err: unknown) {
        let message = "Credenciales inválidas";
        if (axios.isAxiosError(err)) {
          const errorData = err.response?.data;
          message = errorData?.detail || errorData?.non_field_errors?.[0] || message;
        }
        setError(message);
        clearSession();
        return null;
      } finally {
        setLoading(false);
      }
    },
    [clearSession, fetchUserProfile]
  );

  const loginWithGoogle = useCallback(
    async (googleToken: string, tipo: string): Promise<UserProfile | null> => {
      try {
        setLoading(true);
        setError(null);

        const loginData = await apiLoginWithGoogle(googleToken, tipo);
        const { access, refresh } = loginData;

        sessionStorage.setItem("access_token", access);
        sessionStorage.setItem("refresh_token", refresh);
        updateAuthCookies(access);

        setIsAuthenticated(true);
        return await fetchUserProfile();
      } catch (err: unknown) {
        let message = "Error al iniciar sesión con Google";
        if (axios.isAxiosError(err)) {
          const errorData = err.response?.data;
          message = errorData?.detail || message;
        }
        setError(message);
        clearSession();
        return null;
      } finally {
        setLoading(false);
      }
    },
    [clearSession, fetchUserProfile]
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Always clear local state even when API logout fails.
    } finally {
      clearSession();
      router.replace(ROUTES.PUBLIC.LOGIN);
    }
  }, [clearSession, router]);

  useEffect(() => {
    const unsubscribe = subscribeToAuthChanges((newAuthState) => {
      setIsAuthenticated(newAuthState);

      if (!newAuthState) {
        setUser(null);
        clearCachedUser();
      } else if (!userRef.current) {
        const token = sessionStorage.getItem("access_token");
        const cached = readCachedUser();
        if (token && cached && cached.token === token) {
          setUser(cached.user);
          return;
        }
        void fetchUserProfile();
      }
    });

    return unsubscribe;
  }, [fetchUserProfile]);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const isAuthFromStorage = checkStorageAuth();
        if (isAuthFromStorage) {
          const token = sessionStorage.getItem("access_token");
          const cached = readCachedUser();
          syncAuthState();

          if (token && cached && cached.token === token) {
            setUser(cached.user);
            setIsAuthenticated(true);
            setLoading(false);

            const cacheAge = Date.now() - cached.cachedAt;
            if (cacheAge > USER_CACHE_TTL_MS) {
              void fetchUserProfile();
            }
            return;
          }

          await fetchUserProfile();
        } else {
          setLoading(false);
        }
      } catch {
        setLoading(false);
        setIsAuthenticated(false);
      }
    };

    checkAuth();

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === "access_token" || event.key === null) {
        checkStorageAuth();
        syncAuthState();
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [checkStorageAuth, fetchUserProfile]);

  return useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated,
      login,
      loginWithGoogle,
      logout,
      refreshProfile: fetchUserProfile,
    }),
    [error, fetchUserProfile, isAuthenticated, loading, login, loginWithGoogle, logout, user]
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useProvideAuth();
  return React.createElement(AuthContext.Provider, { value: auth }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
