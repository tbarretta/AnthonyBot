/**
 * store/settingsStore.ts
 * Zustand store for app settings, persisted via MMKV.
 *
 * Settings are read synchronously at timer start to avoid async gaps.
 * MMKV provides synchronous read/write, making it ideal for settings that
 * must be available the moment the user presses "Start".
 *
 * TODO: Wire MMKV persistence using zustand-mmkv-storage or a custom persist
 * middleware once the native module is installed:
 *   import { MMKV } from 'react-native-mmkv';
 *   const storage = new MMKV();
 */

import { create } from 'zustand';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Available start beep sounds */
export type BeepSound = 'standard' | 'double' | 'voice_standby' | 'silent';

/** Input mode for shot registration */
export type InputMode = 'microphone' | 'manual';

export interface AppSettings {
  /**
   * Microphone sensitivity / RMS threshold.
   * Range: 0.0 (extremely sensitive) – 1.0 (very loud required).
   * Default: 0.05 (works well in most outdoor ranges)
   */
  sensitivity: number;

  /**
   * Bandpass filter low cutoff (Hz).
   * Frequencies below this are attenuated. Default: 1000Hz.
   */
  minFreq: number;

  /**
   * Bandpass filter high cutoff (Hz).
   * Frequencies above this are attenuated. Default: 8000Hz.
   */
  maxFreq: number;

  /**
   * Minimum interval between shots in milliseconds.
   * Prevents double-triggering from echoes. Default: 80ms.
   */
  minInterval: number;

  /**
   * Default par time in milliseconds.
   * 0 = par time disabled. Default: 0.
   */
  defaultParTime: number;

  /**
   * Minimum random start delay in milliseconds.
   * Default: 1000ms (1 second). IDPA minimum is 1s.
   */
  randomDelayMin: number;

  /**
   * Maximum random start delay in milliseconds.
   * Default: 4000ms (4 seconds). IDPA maximum is 4s.
   */
  randomDelayMax: number;

  /**
   * Default input mode for new runs.
   * Default: 'microphone'.
   */
  inputMode: InputMode;

  /**
   * Start signal sound type.
   * Default: 'standard' (single beep).
   */
  beepSound: BeepSound;
}

export interface SettingsState {
  settings: AppSettings;

  /**
   * Update one or more settings by key.
   * @param patch - Partial settings object with only the keys to update
   */
  updateSetting: (patch: Partial<AppSettings>) => void;

  /**
   * Reset all settings to factory defaults.
   */
  resetSettings: () => void;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

export const DEFAULT_SETTINGS: AppSettings = {
  sensitivity: 0.05,
  minFreq: 1000,
  maxFreq: 8000,
  minInterval: 80,
  defaultParTime: 0,
  randomDelayMin: 1000,
  randomDelayMax: 4000,
  inputMode: 'microphone',
  beepSound: 'standard',
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: { ...DEFAULT_SETTINGS },

  updateSetting: (patch: Partial<AppSettings>) => {
    set((state) => ({
      settings: {
        ...state.settings,
        ...patch,
      },
    }));
    // TODO: Persist to MMKV after update:
    // Object.entries(patch).forEach(([key, value]) => {
    //   storage.set(key, JSON.stringify(value));
    // });
  },

  resetSettings: () => {
    set({ settings: { ...DEFAULT_SETTINGS } });
    // TODO: Clear MMKV keys for settings:
    // Object.keys(DEFAULT_SETTINGS).forEach(key => storage.delete(key));
  },
}));

// ---------------------------------------------------------------------------
// Selector helpers (use these to avoid unnecessary re-renders)
// ---------------------------------------------------------------------------

/** Returns only the audio detection config (used by the shot detection pipeline) */
export const selectAudioConfig = (state: SettingsState) => ({
  sensitivity: state.settings.sensitivity,
  minFreq: state.settings.minFreq,
  maxFreq: state.settings.maxFreq,
  minInterval: state.settings.minInterval,
});
