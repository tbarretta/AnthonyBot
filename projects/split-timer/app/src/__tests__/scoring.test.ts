/**
 * @jest-environment node
 */
import { calcPureTime, calcUSPSA, calcIDPA } from '../services/scoring';
import { Run } from '../models/types';

const mockRun: Run = {
  id: 'test-1',
  createdAt: Date.now(),
  inputMode: 'microphone',
  startSignalAt: 1000,
  shots: [1940, 2710, 3490, 4260], // draw=0.94s, splits: 0.77, 0.78, 0.77
};

describe('Pure Time Scoring', () => {
  it('calculates final time with no penalties', () => {
    const result = calcPureTime(mockRun, 0);
    expect(result.kind).toBe('pure');
    // totalTime is in milliseconds: last shot (4260) - startSignalAt (1000) = 3260ms
    expect(result.totalTime).toBeCloseTo(3260, 0);
    // finalTime is in seconds: 3.26s + 0 penalty = 3.26s
    expect(result.finalTime).toBeCloseTo(3.26, 1);
  });

  it('adds penalty seconds to final time', () => {
    const result = calcPureTime(mockRun, 3); // 3 second penalty
    // finalTime = 3.26s + 3s = 6.26s
    expect(result.finalTime).toBeCloseTo(6.26, 1);
    expect(result.penaltySeconds).toBe(3);
  });
});

describe('USPSA Scoring', () => {
  it('calculates hit factor correctly', () => {
    const result = calcUSPSA(mockRun, 50, { mike: 0, noShoot: 0, procedural: 0 });
    expect(result.kind).toBe('uspsa');
    expect(result.points).toBe(50);
    expect(result.hitFactor).toBeGreaterThan(0);
  });

  it('deducts mike penalties', () => {
    const clean = calcUSPSA(mockRun, 50, { mike: 0, noShoot: 0, procedural: 0 });
    const withMike = calcUSPSA(mockRun, 50, { mike: 1, noShoot: 0, procedural: 0 });
    expect(withMike.hitFactor).toBeLessThan(clean.hitFactor);
  });
});

describe('IDPA Scoring', () => {
  it('calculates final time with penalties', () => {
    const result = calcIDPA(mockRun, { late: 1, miss: 0, procedural: 0, nonThreat: 0 });
    expect(result.kind).toBe('idpa');
    expect(result.finalTime).toBeGreaterThan(result.rawTime);
  });
});
