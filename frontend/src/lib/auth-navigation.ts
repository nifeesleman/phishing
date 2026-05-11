export function getDefaultAuthenticatedPath(isAdmin: boolean) {
  return isAdmin ? "/admin" : "/dashboard";
}

function isSafeRedirectTarget(redirect: string | null | undefined): redirect is string {
  return Boolean(redirect && redirect.startsWith("/") && !redirect.startsWith("//"));
}

export function getRequestedRedirectTarget() {
  if (typeof window === "undefined") return null;

  const redirect = new URLSearchParams(window.location.search).get("redirect");
  return isSafeRedirectTarget(redirect) ? redirect : null;
}

export function getSafeRedirectTarget(fallback = "/dashboard") {
  return getRequestedRedirectTarget() ?? fallback;
}

export function getAuthPagePath(path: string, redirectTarget = getRequestedRedirectTarget()) {
  return redirectTarget ? `${path}?redirect=${encodeURIComponent(redirectTarget)}` : path;
}
