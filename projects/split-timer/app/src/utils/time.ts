/**
 * utils/time.ts
 * Pure time formatting utilities for SplitTimer.
 * All functions are stateless and safe to call anywhere (components, services, tests).
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Pads a number to a fixed width with leading zeros.
 * @param n - The number to pad
 * @param width - Desired total string width
 */
function pad(n: number, width: number): string {
  return String(n).padStart(width, '0');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Format a raw millisecond value as a compact shot time.
 *
 * Examples:
 *   formatMs(1234)    → "1.234"
 *   formatMs(10500)   → "10.500"
 *   formatMs(0)       → "0.000"
 *
 * @param ms - Time in milliseconds (non-negative integer)
 * @returns String formatted as "S.mmm" or "SS.mmm"
 */
export function formatMs(ms: number): string {
  if (ms < 0) ms = 0;
  const totalSeconds = Math.floor(ms / 1000);
  const millis = ms % 1000;
  return `${totalSeconds}.${pad(millis, 3)}`;
}

/**
 * Format a split time (time between shots) as a compact display string.
 * Split times are always shown with a leading "+" to visually distinguish
 * them from draw/total times.
 *
 * Examples:
 *   formatSplit(456)  → "+0.456"
 *   formatSplit(1200) → "+1.200"
 *
 * @param ms - Split duration in milliseconds
 * @returns String formatted as "+S.mmm"
 */
export function formatSplit(ms: number): string {
  return `+${formatMs(ms)}`;
}

/**
 * Format a USPSA hit factor for display.
 * Hit factors are always shown to 4 decimal places per USPSA rules.
 *
 * Examples:
 *   formatHitFactor(7.5)      → "7.5000"
 *   formatHitFactor(12.3456)  → "12.3456"
 *   formatHitFactor(0)        → "0.0000"
 *
 * @param hf - Hit factor (points per second)
 * @returns String formatted to 4 decimal places
 */
export function formatHitFactor(hf: number): string {
  return hf.toFixed(4);
}

/**
 * Format a total run time for prominent display.
 * Shows seconds with two decimal places — matches how most hardware timers display.
 *
 * Examples:
 *   formatTotalTime(1234)  → "1.23"
 *   formatTotalTime(10505) → "10.51"
 *   formatTotalTime(65000) → "65.00"
 *
 * Note: This rounds to 2 decimal places, unlike formatMs which preserves
 * full millisecond precision. Use formatMs() when full precision is needed
 * (e.g. in run detail screens or exports).
 *
 * @param ms - Total time in milliseconds
 * @returns String formatted as "S.cc" (centiseconds)
 */
export function formatTotalTime(ms: number): string {
  if (ms < 0) ms = 0;
  const seconds = ms / 1000;
  return seconds.toFixed(2);
}
