import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: API_BASE_URL });

// Attach JWT if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nexacore_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  localStorage.setItem("nexacore_token", data.access_token);
  return data;
}

export async function register(
  email: string,
  password: string,
  full_name?: string
) {
  const { data } = await api.post("/auth/register", {
    email,
    password,
    full_name: full_name || null,
  });

  return data;
}

export async function requestPasswordReset(email: string) {
  const { data } = await api.post("/auth/forgot-password", { email });
  return data as { message: string; reset_token: string };
}

export async function resetPassword(reset_token: string, new_password: string) {
  const { data } = await api.post("/auth/reset-password", {
    reset_token,
    new_password,
  });
  return data as { message: string };
}

export function logout() {
  localStorage.removeItem("nexacore_token");
}