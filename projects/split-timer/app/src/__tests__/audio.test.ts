/**
 * @jest-environment node
 */
import { calculateRMS, detectOnset, isBelowMinInterval, processShotDetection } from '../utils/audio';

describe('calculateRMS', () => {
  it('returns 0 for empty buffer', () => {
    expect(calculateRMS(new Float32Array(0))).toBe(0);
  });
  it('returns correct RMS for known values', () => {
    const buf = new Float32Array([0.5, -0.5, 0.5, -0.5]);
    expect(calculateRMS(buf)).toBeCloseTo(0.5, 3);
  });
});

describe('detectOnset', () => {
  it('returns false when below threshold', () => {
    expect(detectOnset(0.01, 0.005, 0.1)).toBe(false);
  });
  it('returns true for sudden loud spike', () => {
    expect(detectOnset(0.8, 0.1, 0.3)).toBe(true);
  });
  it('returns false for sustained loud sound (no spike ratio)', () => {
    expect(detectOnset(0.8, 0.75, 0.3)).toBe(false);
  });
});

describe('isBelowMinInterval', () => {
  it('returns false when no previous shot', () => {
    expect(isBelowMinInterval(0, Date.now())).toBe(false);
  });
  it('suppresses shots within 80ms', () => {
    const now = Date.now();
    expect(isBelowMinInterval(now - 50, now, 80)).toBe(true);
  });
  it('allows shots after 80ms', () => {
    const now = Date.now();
    expect(isBelowMinInterval(now - 100, now, 80)).toBe(false);
  });
});

describe('processShotDetection', () => {
  it('detects a shot from a loud spike buffer', () => {
    // Build a buffer with ~4kHz square wave content (44100 / (5*2) ≈ 4410 Hz).
    // This falls within the 1kHz–8kHz bandpass so energy survives filtering.
    // RMS of a full-amplitude square wave ≈ 0.85, far above sensitivity=0.1.
    const buf = new Int16Array(1024);
    for (let i = 0; i < 1024; i++) {
      buf[i] = Math.floor(i / 5) % 2 === 0 ? 28000 : -28000;
    }
    const state = { previousRms: 0.01, lastShotMs: 0 };
    const config = { sensitivity: 0.1, minFreq: 1000, maxFreq: 8000, minInterval: 80 };
    const result = processShotDetection(buf, state, config, Date.now());
    expect(result.shotDetected).toBe(true);
  });

  it('does not detect a shot for a silent buffer', () => {
    const buf = new Int16Array(1024).fill(0);
    const state = { previousRms: 0.01, lastShotMs: 0 };
    const config = { sensitivity: 0.1, minFreq: 1000, maxFreq: 8000, minInterval: 80 };
    const result = processShotDetection(buf, state, config, Date.now());
    expect(result.shotDetected).toBe(false);
  });
});
