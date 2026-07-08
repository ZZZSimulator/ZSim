export function normalizeBackendRelativePath(path: string): string {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    throw new Error('Backend API requests must use a local backend-relative path');
  }
  return path;
}

export function buildBackendRequestPath(path: string, query?: Record<string, unknown>): string {
  const requestPath = normalizeBackendRelativePath(path);
  if (!query) {
    return requestPath;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    params.set(key, String(value));
  }

  const queryString = params.toString();
  if (!queryString) {
    return requestPath;
  }
  return `${requestPath}${requestPath.includes('?') ? '&' : '?'}${queryString}`;
}

export function buildBackendUrl(
  base: string,
  path: string,
  query?: Record<string, unknown>,
): string {
  const url = new URL(buildBackendRequestPath(path, query), base);
  return url.toString();
}
