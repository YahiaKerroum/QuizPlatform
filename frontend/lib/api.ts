"use client";

import axios from "axios";

import { clearToken, getToken } from "@/lib/auth";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let attached = false;

if (!attached) {
  api.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (typeof window !== "undefined" && error.response?.status === 403) {
        const requestUrl = String(error.config?.url ?? "");
        if (requestUrl.startsWith("/admin")) {
          window.location.href = "/dashboard";
        }
      }

      if (typeof window !== "undefined" && error.response?.status === 401) {
        const requestUrl = String(error.config?.url ?? "");
        const pathname = window.location.pathname;
        const isAuthRequest = requestUrl.includes("/auth/login") || requestUrl.includes("/auth/register");
        const isAuthScreen = pathname === "/login" || pathname === "/register";
        const hasToken = Boolean(getToken());

        if (!isAuthRequest && !isAuthScreen && hasToken) {
          clearToken();
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  attached = true;
}

export default api;
