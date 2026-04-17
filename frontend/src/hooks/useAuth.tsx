import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { apiClient } from "../api/client";

interface Staff {
  id: number;
  fullName: string;
  email: string;
}

interface AuthContextType {
  staff: Staff | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = "auth_token";
const STAFF_KEY = "auth_staff";

function readFromStorage() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const staffRaw = localStorage.getItem(STAFF_KEY);
    const staff = staffRaw ? JSON.parse(staffRaw) : null;
    return { token, staff };
  } catch {
    return { token: null, staff: null };
  }
}

function writeToStorage(token: string | null, staff: Staff | null) {
  try {
    if (token && staff) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(STAFF_KEY, JSON.stringify(staff));
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(STAFF_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const { token: storedToken, staff: storedStaff } = readFromStorage();
    if (storedToken && storedStaff) {
      setToken(storedToken);
      setStaff(storedStaff);
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await apiClient.post("/login/", {
        username,
        password,
      });

      const { token: newToken, staff: newStaff } = response.data;

      setToken(newToken);
      setStaff(newStaff);
      writeToStorage(newToken, newStaff);
    } catch (error: any) {
      const message = error.response?.data?.detail || "Identifiants incorrects";
      throw new Error(message);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setStaff(null);
    writeToStorage(null, null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        staff,
        token,
        isAuthenticated: !!token && !!staff,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useRequireAuth() {
  const auth = useAuth();
  return auth;
}
