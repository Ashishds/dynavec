/**
 * Utility functions for resolving URLs across GitHub Pages subpaths and local dev.
 */

export function getLandingUrl(): string {
  if (typeof window === "undefined") {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
    if (basePath) {
      const parent = basePath.replace(/\/dashboard\/?$/, "") || "/";
      return parent.endsWith("/") ? parent : `${parent}/`;
    }
    return "/";
  }

  // 1. If explicit NEXT_PUBLIC_BASE_PATH env var is set (e.g. "/dynavec/dashboard")
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  if (basePath) {
    const parent = basePath.replace(/\/dashboard\/?$/, "") || "/";
    return parent.endsWith("/") ? parent : `${parent}/`;
  }

  // 2. Derive from window.location.pathname (e.g. "/dynavec/dashboard/" -> "/dynavec/")
  const pathname = window.location.pathname;
  if (pathname.includes("/dashboard")) {
    const parent = pathname.split("/dashboard")[0] || "";
    return parent.endsWith("/") ? parent : `${parent}/`;
  }

  // 3. Fallback for relative resolution
  return "../";
}

export function getDashboardBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_BASE_PATH || "";
  }
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  if (basePath) return basePath;
  if (window.location.pathname.includes("/dashboard")) {
    const parts = window.location.pathname.split("/dashboard");
    return `${parts[0]}/dashboard`;
  }
  return "";
}
