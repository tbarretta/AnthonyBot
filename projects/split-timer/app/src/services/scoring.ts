/**
 * services/scoring.ts
 * Pure scoring calculation functions for SplitTimer.
 *
 * All functions are stateless, take explicit inputs, and return scoring result
 * objects typed from models/types.ts. Safe to unit test without any React context.
 */

import type { Run, PureTimeResult, USPSAResult, IDPAResult } from '../models/types';

// ---------------------------------------------------------------------------
// USPSA Penalty Constants
// ---------------------------------------------------------------------------

const USPSA_MIKE_PENALTY = 10;       // points deducted per Mike
const USPSA_NO_SHOOT_PENALTY = 10;   // points deducted per No-Shoot
const USPSA_PROCEDURAL_PENALTY = 10; // points deducted per Procedural

// ---------------------------------------------------------------------------
// IDPA Penalty Constants (seconds)
// ---------------------------------------------------------------------------

const IDPA_LATE_PENALTY = 0.5;       // per hit on target after cover
const IDPA_MISS_PENALTY = 2.5;       // per missed shot
const IDPA_PROCEDURAL_PENALTY = 3.0; // per procedural error
const IDPA_NON_THREAT_PENALTY = 5.0; // per non-threat hit

// ---------------------------------------------------------------------------
// Pure Time Scoring
// ---------------------------------------------------------------------------

/**
 * Calculate Pure Time scoring for a run.
 *
 * Pure Time is the simplest scoring method:
 *   finalTime (seconds) = runTime (seconds) + penaltySeconds
 *
 * Lower final time is better.
 *
 * @param run             - The completed Run record
 * @param penaltySeconds  - Total penalty time in seconds (caller determines per-miss penalty × misses)
 * @returns               - PureTimeResult
 *
 * @example
 * // Run of 5.234s with 2 misses at 0.5s each → finalTime = 6.234s
 * calcPureTime(run, 1.0)
 */
export function calcPureTime(run: Run, penaltySeconds: number): PureTimeResult {
  if (run.shots.length === 0) {
    return { kind: 'pure', totalTime: 0, penaltySeconds, finalTime: penaltySeconds };
  }

  // Total run time in milliseconds (last shot − start signal)
  const totalTimeMs = run.shots[run.shots.length - 1] - run.startSignalAt;
  const totalTimeSec = totalTimeMs / 1000;
  const finalTime = totalTimeSec + penaltySeconds;

  return {
    kind: 'pure',
    totalTime: totalTimeMs,
    penaltySeconds,
    finalTime,
  };
}

// ---------------------------------------------------------------------------
// USPSA Hit Factor Scoring
// ---------------------------------------------------------------------------

/**
 * Calculate USPSA Hit Factor scoring for a run.
 *
 * Hit Factor = (totalPoints − penaltyPoints) / time (seconds)
 * Higher hit factor is better.
 *
 * Standard point values per target zone:
 *   A = 5pts, C = 4pts, D = 2pts, Mike = −10pts, No-Shoot = −10pts
 *
 * The `points` parameter is the raw earned points BEFORE penalty deductions
 * (i.e. sum of all A/C/D hits). Penalty counts are passed separately so
 * the calculation remains transparent and reversible.
 *
 * @param run       - The completed Run record
 * @param points    - Raw points scored (sum of A/C/D zone values)
 * @param penalties - Count of each penalty type
 * @returns         - USPSAResult
 *
 * @example
 * // 6 A-hits (30pts), 2 C-hits (8pts), 1 Mike, time 5.00s
 * // netPoints = 38 - 10 = 28
 * // hitFactor = 28 / 5.00 = 5.6000
 * calcUSPSA(run, 38, { mike: 1, noShoot: 0, procedural: 0 })
 */
export function calcUSPSA(
  run: Run,
  points: number,
  penalties: { mike: number; noShoot: number; procedural: number },
): USPSAResult {
  const totalPenaltyPoints =
    penalties.mike * USPSA_MIKE_PENALTY +
    penalties.noShoot * USPSA_NO_SHOOT_PENALTY +
    penalties.procedural * USPSA_PROCEDURAL_PENALTY;

  const netPoints = Math.max(0, points - totalPenaltyPoints);

  // Time in seconds from start signal to last shot
  let timeSec = 0;
  if (run.shots.length > 0) {
    timeSec = (run.shots[run.shots.length - 1] - run.startSignalAt) / 1000;
  }

  // Avoid division by zero: if time is 0 (e.g. no shots), hitFactor is 0
  const hitFactor = timeSec > 0 ? netPoints / timeSec : 0;

  return {
    kind: 'uspsa',
    points: netPoints,
    time: timeSec,
    hitFactor,
    penalties,
  };
}

// ---------------------------------------------------------------------------
// IDPA Scoring
// ---------------------------------------------------------------------------

/**
 * Calculate IDPA scoring for a run.
 *
 * finalTime = rawTime (seconds) + sum of all penalty seconds
 * Lower final time is better.
 *
 * IDPA penalty values:
 *   - Late hit (behind cover): +0.5s each
 *   - Miss:                    +2.5s each
 *   - Procedural:              +3.0s each
 *   - Non-Threat hit:          +5.0s each
 *
 * @param run       - The completed Run record
 * @param penalties - Count of each penalty type
 * @returns         - IDPAResult
 *
 * @example
 * // Raw time 12.50s, 2 misses, 1 procedural
 * // finalTime = 12.50 + (2 × 2.5) + (1 × 3.0) = 20.50s
 * calcIDPA(run, { late: 0, miss: 2, procedural: 1, nonThreat: 0 })
 */
export function calcIDPA(
  run: Run,
  penalties: { late: number; miss: number; procedural: number; nonThreat: number },
): IDPAResult {
  // Raw time in seconds from start signal to last shot
  let rawTime = 0;
  if (run.shots.length > 0) {
    rawTime = (run.shots[run.shots.length - 1] - run.startSignalAt) / 1000;
  }

  const totalPenaltySec =
    penalties.late * IDPA_LATE_PENALTY +
    penalties.miss * IDPA_MISS_PENALTY +
    penalties.procedural * IDPA_PROCEDURAL_PENALTY +
    penalties.nonThreat * IDPA_NON_THREAT_PENALTY;

  const finalTime = rawTime + totalPenaltySec;

  return {
    kind: 'idpa',
    rawTime,
    penalties,
    finalTime,
  };
}
