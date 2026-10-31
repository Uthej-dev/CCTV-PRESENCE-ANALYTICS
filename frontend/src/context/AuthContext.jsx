import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../api";
import { tokenStore } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  // On load: if a token exists, verify it and fetch the user
  useEffect(() => {
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setReady(true));
  }, []);

  // The API client fires this when any request gets a 401
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const handleAuth = useCallback((res) => {
    tokenStore.set(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      login: (email, password) => authApi.login({ email, password }).then(handleAuth),
      register: (body) => authApi.register(body).then(handleAuth),
      logout: async () => {
        await authApi.logout();
        tokenStore.clear();
        setUser(null);
      },
    }),
    [user, ready, handleAuth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
