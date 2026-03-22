/**
 * utils/audio.ts
 * Shot detection pipeline — pure DSP functions.
 *
 * Pipeline overview:
 *   PCM buffer → bandpassFilter → calculateRMS → detectOnset
 *              → isBelowMinInterval → processShotDetection (orchestrator)
 *
 * All functions are pure (no side effects) and fully unit-testable.
 * The stateful orchestration is handled by useAudioRecorder (hook),
 * which calls processShotDetection on each incoming buffer.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Snapshot of the detector's state between buffer callbacks.
 * Passed into processShotDetection and returned (updated) each call.
 */
export interface ShotDetectionState {
  /** RMS of the previous buffer frame (used for onset ratio comparison) */
  previousRms: number;
  /** Unix ms timestamp of the most recently registered shot (0 if none) */
  lastShotMs: number;
}

/**
 * Configuration values read from settingsStore.
 */
export interface ShotDetectionConfig {
  /** RMS amplitude threshold below which the buffer is ignored (0.0–1.0) */
  sensitivity: number;
  /** Bandpass filter low cutoff in Hz */
  minFreq: number;
  /** Bandpass filter high cutoff in Hz */
  maxFreq: number;
  /** Minimum milliseconds between consecutive shot registrations */
  minInterval: number;
}

/**
 * Result returned by processShotDetection for each buffer.
 */
export interface ShotDetectionResult {
  /** True if a shot was detected in this buffer */
  shotDetected: boolean;
  /** Updated state to pass into the next call */
  nextState: ShotDetectionState;
}

// ---------------------------------------------------------------------------
// 1. Bandpass Filter
// ---------------------------------------------------------------------------

/**
 * Applies a simple two-pass biquad bandpass filter to a PCM Int16 buffer.
 *
 * This is a naive single-pole IIR approximation — not a true biquad — but
 * sufficient for detecting impulsive gunshot onsets in the 1kHz–8kHz band.
 * For a tighter filter, replace with a proper biquad implementation.
 *
 * The filter:
 *   - High-pass at minFreq: removes low-frequency rumble (HVAC, footsteps)
 *   - Low-pass at maxFreq: removes ultrasonic noise and mic self-noise
 *
 * @param buffer     - Raw PCM samples as Int16Array (signed 16-bit, range −32768..32767)
 * @param sampleRate - Sample rate in Hz (typically 44100 or 16000)
 * @param minFreq    - High-pass cutoff frequency in Hz
 * @param maxFreq    - Low-pass cutoff frequency in Hz
 * @returns          - New Float32Array of filtered samples, normalized to −1.0..1.0
 */
export function bandpassFilter(
  buffer: Int16Array,
  sampleRate: number,
  minFreq: number,
  maxFreq: number,
): Float32Array {
  const n = buffer.length;
  const out = new Float32Array(n);

  // Normalize Int16 → Float32 in the same pass
  const normalized = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    normalized[i] = buffer[i] / 32768.0;
  }

  // --- High-pass filter (removes frequencies below minFreq) ---
  // RC time constant for high-pass: RC = 1 / (2π * cutoffHz)
  // Discrete coefficient: α = RC / (RC + dt) where dt = 1/sampleRate
  const rcHp = 1.0 / (2.0 * Math.PI * minFreq);
  const dtHp = 1.0 / sampleRate;
  const alphaHp = rcHp / (rcHp + dtHp);

  const hpOut = new Float32Array(n);
  hpOut[0] = normalized[0];
  for (let i = 1; i < n; i++) {
    // y[i] = α * (y[i-1] + x[i] - x[i-1])
    hpOut[i] = alphaHp * (hpOut[i - 1] + normalized[i] - normalized[i - 1]);
  }

  // --- Low-pass filter (removes frequencies above maxFreq) ---
  // RC time constant for low-pass: RC = 1 / (2π * cutoffHz)
  // Discrete coefficient: α = dt / (RC + dt)
  const rcLp = 1.0 / (2.0 * Math.PI * maxFreq);
  const alphaLp = dtHp / (rcLp + dtHp);

  out[0] = hpOut[0];
  for (let i = 1; i < n; i++) {
    // y[i] = α * x[i] + (1 - α) * y[i-1]
    out[i] = alphaLp * hpOut[i] + (1.0 - alphaLp) * out[i - 1];
  }

  return out;
}

// ---------------------------------------------------------------------------
// 2. RMS Amplitude
// ---------------------------------------------------------------------------

/**
 * Calculates the Root Mean Square (RMS) amplitude of a Float32 audio buffer.
 *
 * RMS is the standard measure of audio loudness. Gunshots produce very high
 * RMS values over a short window, which makes it a reliable trigger.
 *
 * Formula: RMS = sqrt( (1/N) * Σ(x[i]²) )
 *
 * @param buffer - Float32Array of normalized audio samples (−1.0..1.0)
 * @returns      - RMS value in range 0.0..1.0
 */
export function calculateRMS(buffer: Float32Array): number {
  if (buffer.length === 0) return 0;

  let sumOfSquares = 0;
  for (let i = 0; i < buffer.length; i++) {
    sumOfSquares += buffer[i] * buffer[i];
  }

  return Math.sqrt(sumOfSquares / buffer.length);
}

// ---------------------------------------------------------------------------
// 3. Onset Detection
// ---------------------------------------------------------------------------

/**
 * Detects whether a sudden energy onset occurred between two consecutive
 * audio frames. An onset is defined as a sharp spike in RMS level —
 * characteristic of an impulsive transient like a gunshot.
 *
 * Detection criterion:
 *   current RMS > threshold  AND  current RMS / previous RMS > SPIKE_RATIO
 *
 * The SPIKE_RATIO (3.0) means the current frame must be at least 3× louder
 * than the previous frame. This distinguishes sharp transients from
 * sustained loud sounds (music, voices, HVAC).
 *
 * @param currentRms  - RMS of the current buffer frame
 * @param previousRms - RMS of the immediately preceding buffer frame
 * @param threshold   - Minimum RMS to even consider an onset (from settings.sensitivity)
 * @returns           - True if onset detected
 */
export function detectOnset(
  currentRms: number,
  previousRms: number,
  threshold: number,
): boolean {
  const SPIKE_RATIO = 3.0;

  // Gate 1: current frame must exceed the minimum sensitivity threshold
  if (currentRms < threshold) return false;

  // Gate 2: current frame must be a sharp spike vs. the previous frame.
  // Guard against divide-by-zero when previousRms is essentially silent.
  if (previousRms < 0.001) {
    // If previous frame was silent and current exceeds threshold → onset
    return currentRms >= threshold;
  }

  return currentRms / previousRms >= SPIKE_RATIO;
}

// ---------------------------------------------------------------------------
// 4. Minimum Interval Gate
// ---------------------------------------------------------------------------

/**
 * Returns true if the time since the last registered shot is LESS than
 * the minimum interval — meaning a new detection should be suppressed.
 *
 * This prevents double-triggering from:
 *   - Acoustic echos in an indoor range
 *   - Mechanical bounce in the trigger mechanism
 *   - Buffer overlap artefacts in the audio chain
 *
 * Default minimum interval is 80ms, which is faster than any practical
 * split time in competition shooting.
 *
 * @param lastShotMs    - Unix ms timestamp of the last registered shot (0 = none)
 * @param nowMs         - Current Unix ms timestamp
 * @param minIntervalMs - Minimum allowed gap between shots (default: 80ms)
 * @returns             - True if we should SUPPRESS the current detection
 */
export function isBelowMinInterval(
  lastShotMs: number,
  nowMs: number,
  minIntervalMs: number = 80,
): boolean {
  if (lastShotMs === 0) return false; // No previous shot — never suppress
  return nowMs - lastShotMs < minIntervalMs;
}

// ---------------------------------------------------------------------------
// 5. Pipeline Orchestrator
// ---------------------------------------------------------------------------

/**
 * Processes a single PCM audio buffer through the full shot detection pipeline.
 *
 * Call this function on every buffer callback from react-native-audio-record.
 * Pass the returned `nextState` back in on the next call to maintain continuity.
 *
 * Example usage (in useAudioRecorder hook):
 * ```typescript
 * let state: ShotDetectionState = { previousRms: 0, lastShotMs: 0 };
 *
 * AudioRecord.on('data', (data: string) => {
 *   const raw = Buffer.from(data, 'base64');
 *   const int16 = new Int16Array(raw.buffer);
 *   const nowMs = Date.now();
 *
 *   const { shotDetected, nextState } = processShotDetection(int16, state, config, nowMs);
 *   state = nextState;
 *
 *   if (shotDetected) {
 *     timerStore.getState().registerShot(nowMs);
 *   }
 * });
 * ```
 *
 * @param buffer    - Raw PCM Int16Array from the microphone
 * @param state     - Current detector state (previousRms, lastShotMs)
 * @param config    - Settings (sensitivity, minFreq, maxFreq, minInterval)
 * @param nowMs     - Current timestamp in Unix ms (injectable for testability)
 * @returns         - { shotDetected, nextState }
 */
export function processShotDetection(
  buffer: Int16Array,
  state: ShotDetectionState,
  config: ShotDetectionConfig,
  nowMs: number = Date.now(),
): ShotDetectionResult {
  // Step 1: Bandpass filter the raw PCM buffer
  const filtered = bandpassFilter(buffer, 44100, config.minFreq, config.maxFreq);

  // Step 2: Calculate RMS of the filtered frame
  const currentRms = calculateRMS(filtered);

  // Step 3: Check for onset (sharp energy spike)
  const onset = detectOnset(currentRms, state.previousRms, config.sensitivity);

  // Step 4: Check minimum interval gate
  const tooSoon = isBelowMinInterval(state.lastShotMs, nowMs, config.minInterval);

  // Step 5: A shot is registered if onset was detected AND interval gate passed
  const shotDetected = onset && !tooSoon;

  // Build updated state for the next buffer
  const nextState: ShotDetectionState = {
    previousRms: currentRms,
    lastShotMs: shotDetected ? nowMs : state.lastShotMs,
  };

  return { shotDetected, nextState };
}
