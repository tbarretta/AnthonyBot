/**
 * hooks/useSplitStats.ts
 * Derives SplitStats from a Run object.
 *
 * This hook is a pure memoized calculation — it has no side effects and does
 * not touch any store, network, or storage. It re-computes only when the
 * run reference changes.
 */

import { useMemo } from 'react';
import type { Run, SplitStats } from '../models/types';

/**
 * Calculate and return split statistics for a completed run.
 *
 * @param run - A Run object. If null/undefined, returns zeroed stats.
 * @returns SplitStats derived from the run's shot timestamps.
 *
 * @example
 * const stats = useSplitStats(run);
 * console.log(`Draw: ${stats.drawTime}ms`);
 * console.log(`Splits: ${stats.splits.join(', ')}ms`);
 */
export function useSplitStats(run: Run | null | undefined): SplitStats {
  return useMemo(() => {
    // Return zero-value stats if run is missing or has no shots
    if (!run || run.shots.length === 0) {
      return {
        drawTime: 0,
        splits: [],
        totalTime: 0,
        averageSplit: 0,
        parExceeded: false,
      };
    }

    const { shots, startSignalAt, parTime, parExceeded } = run;

    // Draw time: time from start signal to first shot
    const drawTime = shots[0] - startSignalAt;

    // Total time: time from start signal to last shot
    const totalTime = shots[shots.length - 1] - startSignalAt;

    // Splits: time between each consecutive shot (n-1 values)
    const splits: number[] = [];
    for (let i = 1; i < shots.length; i++) {
      splits.push(shots[i] - shots[i - 1]);
    }

    // Average split (mean of all inter-shot intervals)
    const averageSplit =
      splits.length > 0
        ? splits.reduce((sum, s) => sum + s, 0) / splits.length
        : 0;

    // Par exceeded: use stored value if present, otherwise derive from totalTime
    const exceeded =
      parExceeded !== undefined
        ? parExceeded
        : parTime !== undefined && parTime > 0
        ? totalTime > parTime
        : false;

    return {
      drawTime,
      splits,
      totalTime,
      averageSplit,
      parExceeded: exceeded,
    };
  }, [run]);
}
