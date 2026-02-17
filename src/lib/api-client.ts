import type { APIError } from "@/types/models";

/**
 * Fetch JSON from the Next.js API proxy with typed error handling.
 * Throws an APIError-shaped object on non-OK responses.
 */
export async function apiFetch<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, options);

  if (!res.ok) {
    let errorBody: APIError;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = {
        error: "unknown_error",
        message: `Request failed with status ${res.status}`,
      };
    }
    throw errorBody;
  }

  return res.json();
}

/** Extract a user-facing message from an error thrown by apiFetch or TanStack Query. */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "message" in error) {
    return (error as APIError).message || fallback;
  }
  return fallback;
}
