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
      if (typeof window !== "undefined" && error.response?.status === 401) {
        clearToken();
        window.location.href = "/login";
      }
      return Promise.reject(error);
    }
  );

  attached = true;
}

export default api;

