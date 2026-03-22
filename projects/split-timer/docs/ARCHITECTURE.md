# SplitTimer — Architecture Document

**Version:** 1.0  
**Stack:** React Native + TypeScript + Expo

---

## 1. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | React Native (latest stable) + TypeScript | Cross-platform (iOS + Android), typed safety |
| Dev Workflow | Expo managed (bare ejection for audio module) | Fast iteration; bare when native modules require it |
| Navigation | React Navigation v6 (native-stack + bottom-tabs) | Most widely adopted; good TypeScript support |
| State | Zustand | Lightweight, no boilerplate, excellent TypeScript inference |
| Persistent Storage | MMKV (settings) + expo-sqlite (run history) | MMKV: sync, ultra-fast KV for settings. SQLite: relational queries for history/matches |
| Mic Input | react-native-audio-record | PCM buffer callbacks at configurable sample rate |
| Sound Playback | expo-av | Beep / voice start signal playback |
| Haptics | expo-haptics | Par time alert, shot confirmation |
| Subscriptions | react-native-iap (or RevenueCat SDK) | In-app purchases; RevenueCat preferred for receipt validation |
| Export | react-native-share + custom CSV builder | Share sheet integration on both platforms |

---

## 2. Shot Detection Pipeline

The audio pipeline runs on a 50ms PCM buffer loop. All processing is pure JS (no native DSP).

```
┌─────────────────────────────────────────────┐
│  Microphone (react-native-audio-record)      │
│  PCM Int16 buffer @ 44100 Hz, 50ms chunks   │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  Bandpass Filter (1kHz – 8kHz)              │
│  Attenuates low-freq rumble & high-freq hiss│
│  Simple IIR biquad filter (2-pole)          │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  RMS Amplitude Check                        │
│  If RMS < threshold → skip (ambient noise)  │
│  Threshold configurable in Settings         │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  Onset Detection                            │
│  Compares current RMS to previous frame     │
│  Sharp spike (ratio > 3.0) → onset detected │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  Minimum Interval Gate (default: 80ms)      │
│  Ignores detections within 80ms of last shot│
│  Prevents double-triggering from echo       │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  Shot Registered                            │
│  timestamp = Date.now() - buffer latency    │
│  Dispatched to timerStore.registerShot()    │
└─────────────────────────────────────────────┘
```

### Configuration Parameters (settingsStore)

| Param | Default | Description |
|---|---|---|
| `sensitivity` | 0.05 | RMS threshold (0.0–1.0) |
| `minFreq` | 1000 | Bandpass low cutoff (Hz) |
| `maxFreq` | 8000 | Bandpass high cutoff (Hz) |
| `minInterval` | 80 | Min ms between shots |

---

## 3. Data Models

All interfaces defined in `app/src/models/types.ts`.

```typescript
// A single timed run
interface Run {
  id: string;               // UUID
  createdAt: number;        // Unix ms
  label?: string;           // User-assigned label
  notes?: string;
  inputMode: 'microphone' | 'manual';
  startSignalAt: number;    // Timestamp of start beep
  shots: number[];          // Array of shot timestamps (Unix ms)
  parTime?: number;         // Par time in ms
  parExceeded?: boolean;
  matchId?: string;         // Pro: link to Match
  stageId?: string;         // Pro: link to Stage
  division?: string;        // e.g. 'Production', 'CO'
  scoring?: ScoringResult;  // Pro: attached scoring
}

// Derived stats from a Run
interface SplitStats {
  drawTime: number;         // shots[0] - startSignalAt (ms)
  splits: number[];         // shots[n] - shots[n-1] (ms)
  totalTime: number;        // last shot - startSignalAt (ms)
  averageSplit: number;     // mean of splits[]
  parExceeded: boolean;
}

// Scoring variants
interface PureTimeResult {
  kind: 'pure';
  totalTime: number;        // ms
  penaltySeconds: number;   // added penalty
  finalTime: number;        // totalTime/1000 + penaltySeconds
}

interface USPSAResult {
  kind: 'uspsa';
  points: number;           // raw points scored
  time: number;             // run time in seconds
  hitFactor: number;        // points / time
  penalties: {
    mike: number;           // -10 pts each
    noShoot: number;        // -10 pts each
    procedural: number;     // -10 pts each
  };
}

interface IDPAResult {
  kind: 'idpa';
  rawTime: number;          // seconds
  penalties: {
    late: number;           // 0.5s each (hit after cover)
    miss: number;           // 2.5s each
    procedural: number;     // 3.0s each
    nonThreat: number;      // 5.0s each
  };
  finalTime: number;        // rawTime + all penalty seconds
}

type ScoringResult = PureTimeResult | USPSAResult | IDPAResult;

// Pro: Match container
interface Match {
  id: string;
  name: string;
  date: number;             // Unix ms
  division?: string;
  stages: Stage[];
}

// Pro: Stage within a match
interface Stage {
  id: string;
  matchId: string;
  name: string;
  maxPoints?: number;       // USPSA max points for stage
  minimumRounds?: number;
  runs: Run[];
}
```

---

## 4. Screen Navigation Map

```
Bottom Tab Navigator
├── [Timer Tab]       → TimerStack
│   ├── TimerHome
│   ├── InputModeSelect
│   ├── TimerReady        (countdown screen)
│   ├── TimerRunning      (live shot display)
│   ├── RunReview         (post-run split analysis)
│   └── SaveRun           (label, notes, scoring entry)
│
├── [History Tab]     → HistoryStack
│   ├── HistoryList
│   ├── RunDetail
│   └── EditRun
│
├── [Stats Tab]       → StatsStack
│   └── StatsOverview
│
└── [Settings Tab]    → SettingsStack
    ├── SettingsHome
    ├── AudioSettings
    ├── StartSignal
    ├── ParTime
    ├── Subscription
    └── About

Pro Screens (accessed from SaveRun / MatchList):
├── ScoringEntry          (ProGate-wrapped)
├── MatchList             (ProGate-wrapped)
│   └── MatchDetail
│       └── StageDetail
```

---

## 5. Feature Gating

### `useProAccess` Hook

Located at `app/src/hooks/useProAccess.ts`.

Returns:
```typescript
{
  isPro: boolean;
  isTrialActive: boolean;
  trialDaysRemaining: number;
}
```

Implementation plan:
1. On app launch, check subscription status via `react-native-iap` or RevenueCat SDK.
2. Cache result in MMKV with a 24-hour TTL for offline use.
3. On foreground resume, re-validate if TTL has expired.

### `ProGate` Component

Located at `app/src/components/ProGate.tsx`.

Usage:
```tsx
<ProGate>
  <ScoringEntryScreen />
</ProGate>
```

If `isPro || isTrialActive`: renders `children`.  
Otherwise: renders upgrade prompt with "Start Free Trial" and "Learn More" CTAs.

---

## 6. Storage Strategy

| Data | Store | Reason |
|---|---|---|
| Settings | MMKV | Synchronous reads needed on timer start |
| Run history | expo-sqlite | Queryable, supports filters & aggregation |
| Match/Stage data | expo-sqlite | Relational (Stage → Run FK) |
| Pro status cache | MMKV | Fast check on every screen mount |

### SQLite Schema (planned)

```sql
CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  created_at INTEGER,
  label TEXT,
  notes TEXT,
  input_mode TEXT,
  start_signal_at INTEGER,
  shots TEXT,        -- JSON array of timestamps
  par_time INTEGER,
  par_exceeded INTEGER,
  match_id TEXT,
  stage_id TEXT,
  division TEXT,
  scoring TEXT       -- JSON blob
);

CREATE TABLE matches (
  id TEXT PRIMARY KEY,
  name TEXT,
  date INTEGER,
  division TEXT
);

CREATE TABLE stages (
  id TEXT PRIMARY KEY,
  match_id TEXT,
  name TEXT,
  max_points INTEGER,
  minimum_rounds INTEGER,
  FOREIGN KEY (match_id) REFERENCES matches(id)
);
```

---

## 7. Folder Structure

```
split-timer/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── REQUIREMENTS.md
└── app/
    └── src/
        ├── models/
        │   └── types.ts              ← All TypeScript interfaces
        ├── utils/
        │   ├── time.ts               ← Time formatting utilities
        │   └── audio.ts              ← Shot detection DSP (pure functions)
        ├── services/
        │   ├── scoring.ts            ← USPSA/IDPA/PureTime calculation
        │   ├── storage.ts            ← SQLite CRUD for runs/matches/stages
        │   └── export.ts             ← CSV generation + share sheet
        ├── store/
        │   ├── timerStore.ts         ← Zustand: timer state machine
        │   └── settingsStore.ts      ← Zustand: persisted settings (MMKV)
        ├── hooks/
        │   ├── useSplitStats.ts      ← Derives SplitStats from a Run
        │   ├── useProAccess.ts       ← Pro subscription status
        │   ├── useAudioRecorder.ts   ← Mic lifecycle + shot detection loop
        │   └── useRunHistory.ts      ← SQLite run queries
        ├── components/
        │   ├── ProGate.tsx           ← Pro feature gate wrapper
        │   ├── SplitList.tsx         ← Reusable split time list
        │   ├── TimerDisplay.tsx      ← Large time display widget
        │   └── ShotDot.tsx           ← Visual shot indicator
        └── screens/
            ├── timer/
            │   ├── TimerHome.tsx
            │   ├── InputModeSelect.tsx
            │   ├── TimerReady.tsx
            │   ├── TimerRunning.tsx
            │   ├── RunReview.tsx
            │   └── SaveRun.tsx
            ├── history/
            │   ├── HistoryList.tsx
            │   ├── RunDetail.tsx
            │   └── EditRun.tsx
            ├── stats/
            │   └── StatsOverview.tsx
            ├── settings/
            │   ├── SettingsHome.tsx
            │   ├── AudioSettings.tsx
            │   ├── StartSignal.tsx
            │   ├── ParTime.tsx
            │   ├── Subscription.tsx
            │   └── About.tsx
            └── pro/
                ├── ScoringEntry.tsx
                ├── MatchList.tsx
                ├── MatchDetail.tsx
                └── StageDetail.tsx
```

---

## 8. Performance Considerations

- **Audio loop on JS thread:** The 50ms PCM callback + DSP runs on the JS thread. If frame drops are observed, migrate to a `react-native-worklets-core` worklet or a native module.
- **SQLite queries:** All DB reads/writes are async. Use `useMemo` + `useEffect` to avoid redundant queries on re-renders.
- **Timer display:** `TimerRunning` uses `requestAnimationFrame` or `setInterval(16ms)` for the live elapsed display. Avoid heavy re-renders in this screen.
- **MMKV settings:** Read synchronously at timer start to avoid async gaps between user action and timer launch.
