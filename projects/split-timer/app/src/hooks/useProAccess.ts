/**
 * hooks/useProAccess.ts
 * Returns the current user's Pro subscription status.
 *
 * TODO: Replace stub with real IAP integration.
 *
 * Integration options:
 *   A) RevenueCat SDK (recommended):
 *      - Install: `npm install react-native-purchases`
 *      - On app launch: Purchases.configure({ apiKey: '...' })
 *      - Here: const info = await Purchases.getCustomerInfo()
 *              isPro = info.entitlements.active['pro'] !== undefined
 *
 *   B) react-native-iap (manual):
 *      - Install: `npm install react-native-iap`
 *      - Manage receipts and validation manually
 *      - More complex; RevenueCat is preferred for new projects
 *
 * Caching strategy (implement with MMKV):
 *   - Cache `isPro` and `trialDaysRemaining` with a 24-hour TTL
 *   - Re-validate on app foreground if TTL expired
 *   - Always return cached value while validation is in-flight
 */

import { useMemo } from 'react';

export interface ProAccess {
  /** True if the user has an active paid Professional subscription */
  isPro: boolean;
  /** True if the user is within their free trial period */
  isTrialActive: boolean;
  /** Days remaining in free trial (0 if not in trial) */
  trialDaysRemaining: number;
}

/**
 * Returns the Pro access status for the current user.
 *
 * Currently returns a stub with Pro disabled. Replace the internals
 * with real IAP/RevenueCat logic before shipping.
 *
 * @returns ProAccess object
 */
export function useProAccess(): ProAccess {
  // TODO: Replace with real IAP/RevenueCat subscription check
  // See integration notes above.
  return useMemo(
    () => ({
      isPro: false,
      isTrialActive: false,
      trialDaysRemaining: 0,
    }),
    [],
  );
}
