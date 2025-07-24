/**
 * WebSocket Utility Functions
 * Provides secure WebSocket protocol detection and URL building
 */

/**
 * Get the appropriate WebSocket protocol based on the current page protocol
 * Always uses wss: (secure) for production safety
 * @returns 'wss:' for secure WebSocket connections
 */
export function getWebSocketProtocol(): string {
  if (typeof window === 'undefined') {
    return 'wss:';
  }
  // Always use secure WebSocket protocol
  return 'wss:';
}

/**
 * Build a secure WebSocket URL
 * @param host - The host (without protocol)
 * @param path - The path (with leading slash)
 * @param token - Optional authentication token
 * @returns Complete WebSocket URL with wss:// protocol
 */
export function buildWebSocketUrl(host: string, path: string, token?: string): string {
  const protocol = getWebSocketProtocol();
  const tokenParam = token ? `?token=${token}` : '';
  return `${protocol}//${host}${path}${tokenParam}`;
}
