import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export const getAccessToken = () => sessionStorage.getItem("access_token");

export const getRefreshToken = () => sessionStorage.getItem("refresh_token");

export const clearAuthTokens = () => {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
};

export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await axios.post(
      `${API_URL}token/refresh/`,
      { refresh: refreshToken },
      { headers: { "Content-Type": "application/json" } }
    );
    const access = response.data?.access;
    if (!access) return null;
    const rotatedRefresh = response.data?.refresh;
    sessionStorage.setItem("access_token", access);
    if (rotatedRefresh) {
      sessionStorage.setItem("refresh_token", rotatedRefresh);
    }
    return access;
  } catch {
    clearAuthTokens();
    return null;
  }
};
