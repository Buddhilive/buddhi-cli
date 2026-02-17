/**
 * Format bytes into a human-readable string.
 * @example formatBytes(1536) // "1.50 KB"
 * @example formatBytes(0)    // "0 B"
 */
export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Format a number with compact notation (e.g., 1.2K, 3.4M).
 */
export function formatCompact(num: number): string {
  return Intl.NumberFormat("en", { notation: "compact" }).format(num);
}

/**
 * Format an ISO date string to a localized date.
 */
export function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
