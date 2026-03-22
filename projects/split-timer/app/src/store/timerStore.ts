/**
 * store/timerStore.ts
 * Zustand store for the timer state machine.
 *
 * State machine transitions:
 *   idle → countdown → running → review → idle
 *
 * Actions:
 *   startCountdown  — begin the pre-start delay countdown
 *   registerShot    — record a shot timestamp (called by audio pipeline or manual tap)
 *   stopRun         — end the run and move to review
 *   resetRun        — return to idle, clearing all shot data
 *   deleteShot      — remove a shot by index (used in run review edit mode)
 *   addShot         — insert a manual shot timestamp (used in manual input mode)
 */

import { create } from 'zustand';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** The timer's current phase */
export type TimerStatus = 'idle' | 'countdown' | 'running' | 'review';

/** Input mode determines how shots are registered */
export type InputMode = 'microphone' | 'manual';

export interface TimerState {
  // ----- State -----
  /** Current phase of the timer */
  status: TimerStatus;
  /** Array of Unix ms timestamps — one per registered shot */
  shots: number[];
  /** Unix ms when the start signal (beep) fired. 0 when not running. */
  startSignalAt: number;
  /** How shots are being registered in this run */
  inputMode: InputMode;

  // ----- Actions -----
  /**
   * Begin the countdown phase.
   * Sets status to 'countdown'. The caller (TimerReady screen) is responsible
   * for managing the actual countdown delay and calling signalStart().
   * @param mode - Input mode for the upcoming run
   */
  startCountdown: (mode: InputMode) => void;

  /**
   * Fire the start signal. Transitions to 'running' and records the signal timestamp.
   * @param signalAt - Unix ms when the beep fired (defaults to Date.now())
   */
  signalStart: (signalAt?: number) => void;

  /**
   * Register a detected or tapped shot. Only valid while status === 'running'.
   * @param timestamp - Unix ms of the shot (defaults to Date.now())
   */
  registerShot: (timestamp?: number) => void;

  /**
   * Stop the run and transition to review state.
   * Called manually (user taps stop) or automatically (par time exceeded).
   */
  stopRun: () => void;

  /**
   * Reset all run state and return to idle.
   * Called after saving a run or discarding.
   */
  resetRun: () => void;

  /**
   * Delete a specific shot from the shots array by index.
   * Used in run review to correct false positives.
   * Only valid while status === 'review'.
   * @param index - Zero-based index into shots[]
   */
  deleteShot: (index: number) => void;

  /**
   * Insert a manual shot at a specific timestamp.
   * Used in manual input mode to add a missed tap, or in review to insert missed shots.
   * @param timestamp - Unix ms of the shot to insert
   */
  addShot: (timestamp: number) => void;
}

// ---------------------------------------------------------------------------
// Initial State
// ---------------------------------------------------------------------------

const initialState = {
  status: 'idle' as TimerStatus,
  shots: [] as number[],
  startSignalAt: 0,
  inputMode: 'microphone' as InputMode,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useTimerStore = create<TimerState>((set, get) => ({
  ...initialState,

  startCountdown: (mode: InputMode) => {
    set({
      status: 'countdown',
      shots: [],
      startSignalAt: 0,
      inputMode: mode,
    });
  },

  signalStart: (signalAt?: number) => {
    // Only transition from countdown → running
    if (get().status !== 'countdown') return;
    set({
      status: 'running',
      startSignalAt: signalAt ?? Date.now(),
    });
  },

  registerShot: (timestamp?: number) => {
    // Only accept shots while the timer is actively running
    if (get().status !== 'running') return;
    const ts = timestamp ?? Date.now();
    set((state) => ({
      shots: [...state.shots, ts],
    }));
  },

  stopRun: () => {
    const { status } = get();
    if (status !== 'running') return;
    set({ status: 'review' });
  },

  resetRun: () => {
    set({ ...initialState });
  },

  deleteShot: (index: number) => {
    if (get().status !== 'review') return;
    set((state) => ({
      shots: state.shots.filter((_, i) => i !== index),
    }));
  },

  addShot: (timestamp: number) => {
    set((state) => {
      // Insert in sorted order by timestamp
      const newShots = [...state.shots, timestamp].sort((a, b) => a - b);
      return { shots: newShots };
    });
  },
}));
