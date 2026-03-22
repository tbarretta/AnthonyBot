# SplitTimer — Product Requirements Document

**Version:** 1.0  
**Status:** Draft  
**Platforms:** Android 10+, iOS 14+

---

## 1. Overview

SplitTimer is a competitive shooting timer application that replaces dedicated hardware timers (e.g., Competition Electronics ProTimer, PACT Club Timer) with a smartphone app. It is designed for USPSA, IDPA, and general speed shooting practice.

The app listens for gunshots through the device microphone, timestamps each detected shot, and presents draw time, split times, and stage totals in real time.

---

## 2. User Personas

| Persona | Description |
|---|---|
| **Casual Practitioner** | Shoots a few times a month, wants a free, simple timer. Standard tier. |
| **Club Competitor** | Shoots matches regularly. Needs scoring, match tracking. Professional tier. |
| **Squad RO / Score Keeper** | Uses the app to time and score other shooters at a match. Professional tier. |

---

## 3. Tier Definitions

### 3.1 Standard (Free)

No payment or account required. Available immediately on install.

**Core Timer Features:**
- REQ-S-01: Microphone shot detection (configurable sensitivity threshold)
- REQ-S-02: Manual tap input mode (accessibility + indoor dry fire)
- REQ-S-03: Randomized start delay (1.0–4.0s, IDPA-compliant range)
- REQ-S-04: Configurable par time with audible beep and haptic alert
- REQ-S-05: Real-time split display during a run
- REQ-S-06: Draw time prominently displayed post-run
- REQ-S-07: Individual shot timestamps available in run review

**History:**
- REQ-S-08: Store last 50 runs locally (FIFO eviction)
- REQ-S-09: View run detail (all split times, draw, total)
- REQ-S-10: Delete individual runs

**Export:**
- REQ-S-11: Export a run as CSV (share via system share sheet)

**Settings:**
- REQ-S-12: Audio sensitivity (threshold slider)
- REQ-S-13: Microphone frequency range (bandpass min/max)
- REQ-S-14: Minimum interval gate (default 80ms)
- REQ-S-15: Start signal type: beep / voice count / silent
- REQ-S-16: Par time default
- REQ-S-17: Randomized delay range (min/max seconds)

---

### 3.2 Professional ($1.99/month)

Subscription billed monthly via App Store / Google Play. Includes a 7-day free trial.

**Everything in Standard, plus:**

**Scoring:**
- REQ-P-01: Pure Time scoring (time + configurable penalty seconds per miss/procedural)
- REQ-P-02: USPSA Hit Factor scoring (points ÷ time, with Mike / No-Shoot / Procedural penalties)
- REQ-P-03: IDPA scoring (raw time + late penalty + miss + procedural + non-threat penalties)
- REQ-P-04: Scoring entry screen after each run

**Match Management:**
- REQ-P-05: Create / edit / delete Matches
- REQ-P-06: Create / edit / delete Stages within a match
- REQ-P-07: Associate a Run with a Stage
- REQ-P-08: Stage summary view (all runs for a stage, best run highlighted)
- REQ-P-09: Match summary view (aggregated scores across stages)

**History:**
- REQ-P-10: Unlimited run history (SQLite-backed)
- REQ-P-11: Filter history by match, stage, division, date range

**Stats:**
- REQ-P-12: Average draw time trend (last 30 / 90 days)
- REQ-P-13: Average split time trend
- REQ-P-14: Hit factor trend (USPSA)
- REQ-P-15: Run comparison (overlay two runs' splits)

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Shot detection latency ≤ 10ms from audio onset to timestamp |
| NFR-02 | App must request microphone permission before first use; degrade gracefully if denied |
| NFR-03 | App must function fully offline (no network required for core timer) |
| NFR-04 | All local data must persist across app restarts |
| NFR-05 | Subscription status must be verified at app launch and cached for 24h offline use |
| NFR-06 | CSV export must be UTF-8 encoded and compatible with Excel/Google Sheets |
| NFR-07 | App must not crash if audio hardware is unavailable (tablet without mic, etc.) |
| NFR-08 | Timer screen must remain responsive (no dropped UI frames) during recording |

---

## 5. Permissions

| Permission | Platform | Reason |
|---|---|---|
| `RECORD_AUDIO` / `NSMicrophoneUsageDescription` | Android / iOS | Shot detection |
| `VIBRATE` | Android | Haptic par alert |
| No network permission required for core features | — | — |

---

## 6. Out of Scope (v1.0)

- Cloud sync / backup
- Multi-shooter sessions (squad scoring)
- Video recording
- Bluetooth external timer integration
- Web dashboard
- Social/sharing features beyond CSV export

---

## 7. Acceptance Criteria (Selected)

### Timer Core
- AC-1: Given mic permission is granted and a shot is fired at > threshold dB, a timestamp is recorded within 10ms of audio onset.
- AC-2: Given par time is set to 3.00s, a beep and haptic fire at exactly 3.00s ± 50ms after the start signal.
- AC-3: Given minimum interval is 80ms, two shots fired 50ms apart register as one shot.

### Pro Gating
- AC-4: Given user is on Standard tier, navigating to a Pro screen shows the ProGate upgrade prompt.
- AC-5: Given user has an active Professional subscription, all Pro screens are accessible without upgrade prompt.
- AC-6: Given subscription expires, Pro features become inaccessible on next app launch.

### Scoring
- AC-7: Given a USPSA run with 10 points, 3 A-hits (5pts), 2 C-hits (4pts ea), 1 Mike, time 5.00s: hitFactor = (3×5 + 2×4 - 1×10) / 5.00 = 1.40.
- AC-8: Given an IDPA run with rawTime 12.50s, 2 misses (0.5s each), 1 procedural (3s): finalTime = 12.50 + 1.00 + 3.00 = 16.50s.
