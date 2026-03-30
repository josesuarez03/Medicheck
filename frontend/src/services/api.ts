import axios from "axios";
import { LoginResponse } from "@/types/auth";
import { UserProfile, RegisterData, ProfileUpdateData } from "@/types/user";
import { clearAuthTokens, getAccessToken, getRefreshToken, refreshAccessToken } from "@/services/authTokens";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const API = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 10000,
  withCredentials: true,
});

API.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest) return Promise.reject(error);

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = getRefreshToken();

      if (!refreshToken) {
        return Promise.reject(error);
      }

      try {
        const access = await refreshAccessToken();
        if (!access) {
          return Promise.reject(error);
        }
        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${access}`,
        };
        return API(originalRequest);
      } catch (refreshError) {
        clearAuthTokens();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const login = async (username_or_email: string, password: string): Promise<LoginResponse> => {
  const isEmail = username_or_email.includes("@");
  const credentials = isEmail
    ? { email: username_or_email, password }
    : { username: username_or_email, password };

  const response = await API.post("login/", credentials);
  return response.data;
};

export const loginWithGoogle = async (
  token: string,
  profile_type: string
): Promise<LoginResponse> => {
  const response = await API.post("google/login/", {
    token,
    tipo: profile_type,
    profile_type,
  });
  if (response.status !== 200) {
    throw new Error("Error al iniciar sesión con Google");
  }
  return response.data;
};

export const register = async (data: RegisterData): Promise<LoginResponse> => {
  const response = await API.post("register/", data);
  return response.data;
};

export const getUserProfile = async (): Promise<UserProfile> => {
  const token = getAccessToken();
  if (!token) {
    throw new Error("No hay token de acceso disponible");
  }

  const response = await API.get("profile/", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const updateUserProfile = async (data: ProfileUpdateData): Promise<UserProfile> => {
  const response = await API.put("profile/", data);
  return response.data;
};

export const completeProfile = async (data: unknown): Promise<UserProfile> => {
  const response = await API.post("complete/", data);
  return response.data;
};

export const logout = async (): Promise<void> => {
  try {
    const refreshToken = sessionStorage.getItem("refresh_token");
    if (refreshToken) {
      await API.post("logout/", { refresh: refreshToken });
    } else {
      await API.post("logout/");
    }
  } finally {
    clearAuthTokens();
  }
};

export const deleteUser = async (password: string): Promise<void> => {
  await API.delete("account/delete/", {
    data: { password },
  });

  clearAuthTokens();
};

export const changePassword = async (data: {
  old_password: string;
  new_password: string;
  confirm_password: string;
}): Promise<void> => {
  const response = await API.post("password/change/", data);
  if (response.status !== 200) {
    throw new Error("Error al cambiar la contraseña");
  }
};

export default API;
