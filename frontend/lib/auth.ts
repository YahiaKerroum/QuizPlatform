const TOKEN_KEY = "quiz_token";

type CookieOptions = {
  maxAgeSeconds: number;
};


function setTokenCookie(token: string, options: CookieOptions): void {
  document.cookie = `token=${token}; path=/; max-age=${options.maxAgeSeconds}; SameSite=Lax`;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
  setTokenCookie(token, { maxAgeSeconds: 60 * 60 * 24 * 7 });
}

export function setTokenWithExpiry(token: string, expiresInSeconds: number): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
  setTokenCookie(token, { maxAgeSeconds: Math.max(60, expiresInSeconds) });
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  document.cookie = "token=; path=/; max-age=0; SameSite=Lax";
}
