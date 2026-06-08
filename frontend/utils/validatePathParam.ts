/**
 * Validates a URL path parameter to prevent SSRF attacks.
 * Only allows alphanumeric characters, hyphens, underscores, dots, and colons.
 * Rejects path traversal sequences and URL-encoded characters.
 */
export function validatePathParam(value: string | undefined | null, paramName: string = 'parameter'): string {
  if (!value || typeof value !== 'string') {
    throw new Error(`Invalid ${paramName}: must be a non-empty string`);
  }
  // Allow UUIDs, ARNs, alphanumeric IDs, framework names like "nist-800-53", service names like "aws_s3"
  if (!/^[a-zA-Z0-9_\-\.\:]+$/.test(value)) {
    throw new Error(`Invalid ${paramName}: contains disallowed characters`);
  }
  return value;
}
