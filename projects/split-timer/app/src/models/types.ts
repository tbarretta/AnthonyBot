/**
 * models/types.ts
 * Core TypeScript interfaces for SplitTimer.
 * All data flowing through stores, services, and screens is typed here.
 */

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

/**
 * A single timed run captured by the timer.
 * `shots` is an array of Unix millisecond timestamps — one per detected shot.
 * The first element is the draw shot; subsequent elements are follow-up shots.
 */
export interface Run {
  /** UUID v4 */
  id: string;
  /** Unix ms — when the run was saved */
  createdAt: number;
  /** Optional user-assigned label (e.g. "Stage 3 practice") */
  label?: string;
  /** Optional freeform notes */
  notes?: string;
  /** How shots were captured */
  inputMode: 'microphone' | 'manual';
  /** Unix ms — when the start signal fired (beep timestamp) */
  startSignalAt: number;
  /** Array of Unix ms timestamps, one per detected/registered shot */
  shots: number[];
  /** Par time in milliseconds */
  parTime?: number;
  /** True if the last shot exceeded parTime */
  parExceeded?: boolean;
  /** Pro: UUID of the Match this run belongs to */
  matchId?: string;
  /** Pro: UUID of the Stage this run belongs to */
  stageId?: string;
  /** Shooting division (e.g. "Production", "Carry Optics", "CDP") */
  division?: string;
  /** Pro: attached scoring result (applied after run review) */
  scoring?: ScoringResult;
}

// ---------------------------------------------------------------------------
// Split Stats
// ---------------------------------------------------------------------------

/**
 * Derived statistics from a Run. Calculated by useSplitStats() hook.
 */
export interface SplitStats {
  /** Time from start signal to first shot (ms) */
  drawTime: number;
  /** Time between each consecutive shot (ms). Length = shots.length - 1 */
  splits: number[];
  /** Time from start signal to last shot (ms) */
  totalTime: number;
  /** Mean of all values in splits[] (ms) */
  averageSplit: number;
  /** Whether any shot exceeded parTime */
  parExceeded: boolean;
}

// ---------------------------------------------------------------------------
// Scoring Results
// ---------------------------------------------------------------------------

/**
 * Pure Time scoring: total run time + fixed penalty seconds per error.
 * Used for general practice or clubs without USPSA/IDPA rules.
 */
export interface PureTimeResult {
  kind: 'pure';
  /** Raw run time in milliseconds */
  totalTime: number;
  /** Penalty seconds added (e.g. 0.5s per miss) */
  penaltySeconds: number;
  /** Final score: (totalTime / 1000) + penaltySeconds, in seconds */
  finalTime: number;
}

/**
 * USPSA Hit Factor scoring.
 * hitFactor = points / time (higher is better).
 *
 * Standard penalties:
 *  - Mike (M):      -10 points
 *  - No-Shoot (NS): -10 points
 *  - Procedural (P): -10 points
 */
export interface USPSAResult {
  kind: 'uspsa';
  /** Total points scored (before penalties) */
  points: number;
  /** Run time in seconds */
  time: number;
  /** Calculated hit factor = (points - penalties) / time */
  hitFactor: number;
  penalties: {
    /** Number of Mike (miss) hits */
    mike: number;
    /** Number of No-Shoot hits */
    noShoot: number;
    /** Number of Procedural penalties */
    procedural: number;
  };
}

/**
 * IDPA scoring.
 * finalTime = rawTime + sum of all penalty seconds (lower is better).
 *
 * Standard penalty values:
 *  - Late hit (behind cover): +0.5s each
 *  - Miss:                    +2.5s each
 *  - Procedural:              +3.0s each
 *  - Non-Threat hit:          +5.0s each
 */
export interface IDPAResult {
  kind: 'idpa';
  /** Raw run time in seconds */
  rawTime: number;
  penalties: {
    /** Hits on target from behind cover (0.5s each) */
    late: number;
    /** Missed shots (2.5s each) */
    miss: number;
    /** Procedural errors (3.0s each) */
    procedural: number;
    /** Non-threat hits (5.0s each) */
    nonThreat: number;
  };
  /** Final computed time in seconds */
  finalTime: number;
}

/** Discriminated union of all scoring result types */
export type ScoringResult = PureTimeResult | USPSAResult | IDPAResult;

// ---------------------------------------------------------------------------
// Match & Stage (Pro)
// ---------------------------------------------------------------------------

/**
 * A competitive match containing one or more stages.
 * Pro tier only.
 */
export interface Match {
  /** UUID v4 */
  id: string;
  /** Match name (e.g. "April USPSA Club Match") */
  name: string;
  /** Unix ms — match date */
  date: number;
  /** Shooting division for this match */
  division?: string;
  /** Stages within this match */
  stages: Stage[];
}

/**
 * A single stage within a match.
 * Pro tier only.
 */
export interface Stage {
  /** UUID v4 */
  id: string;
  /** Parent match UUID */
  matchId: string;
  /** Stage name (e.g. "Stage 1 – El Presidente") */
  name: string;
  /** USPSA: total available points for this stage */
  maxPoints?: number;
  /** Minimum round count for the stage */
  minimumRounds?: number;
  /** All runs recorded on this stage */
  runs: Run[];
}
