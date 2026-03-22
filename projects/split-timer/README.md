# SplitTimer

A competitive shooting timer app for Android and iOS built with React Native and Expo.

SplitTimer records shot times, split times, and stage totals for competitive shooters practicing USPSA, IDPA, or general speed shooting. It listens for gunshots via the device microphone, timestamps each shot with sub-millisecond precision, and provides detailed split analysis, match management, and scoring.

---

## Features

### Standard (Free)
- Microphone-based shot detection with configurable sensitivity
- Manual tap input mode
- Draw time + split time display
- Par time with audio/haptic alert
- Randomized start delay (IDPA-legal)
- Run history (last 50 runs)
- Basic stats overview
- CSV export

### Professional ($1.99/month)
- Everything in Standard, plus:
- USPSA hit factor scoring
- IDPA scoring with penalty calculation
- Match & stage management
- Unlimited run history
- Advanced stats (trends, comparison charts)
- Cloud backup (future)

---

## Tech Stack

| Layer | Library |
|---|---|
| Framework | React Native + TypeScript |
| Dev tooling | Expo (managed/bare hybrid) |
| Navigation | React Navigation v6 |
| State | Zustand |
| Storage | MMKV + expo-sqlite |
| Microphone | react-native-audio-record |
| Playback | expo-av |
| Haptics | expo-haptics |
| Subscriptions | react-native-iap (or RevenueCat) |
| Export | react-native-share + custom CSV |

---

## Project Structure

```
split-timer/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── REQUIREMENTS.md
└── app/
    └── src/
        ├── models/          # TypeScript interfaces
        ├── utils/           # Pure utility functions (time formatting, audio DSP)
        ├── services/        # Business logic (scoring, storage, export)
        ├── store/           # Zustand stores (timer, settings)
        ├── hooks/           # React hooks (useSplitStats, useProAccess, etc.)
        ├── components/      # Shared UI components (ProGate, etc.)
        └── screens/
            ├── timer/       # Timer flow screens
            ├── history/     # Run history screens
            ├── stats/       # Stats overview
            ├── settings/    # App settings screens
            └── pro/         # Pro-gated screens (scoring, match management)
```

---

## Setup

> ⚠️ This scaffold does not include `package.json` or native build folders yet. These steps are for when the project is initialized.

### Prerequisites

- Node.js 18+
- Expo CLI: `npm install -g expo-cli`
- EAS CLI (for builds): `npm install -g eas-cli`
- iOS: Xcode 14+ (Mac only)
- Android: Android Studio + SDK 33+

### Initialize

```bash
cd app/
npx create-expo-app . --template expo-template-blank-typescript
```

### Install Dependencies

```bash
npx expo install react-native-audio-record expo-av expo-haptics
npx expo install react-navigation/native react-navigation/bottom-tabs react-navigation/native-stack
npx expo install zustand react-native-mmkv expo-sqlite
npx expo install react-native-iap react-native-share
```

### Run

```bash
npx expo start
```

### Build (EAS)

```bash
eas build --platform android
eas build --platform ios
```

---

## Development Notes

- Shot detection runs on the JS thread via a 50ms PCM buffer callback. For production, consider offloading to a native module or worklet.
- MMKV is used for settings persistence (fast sync reads). SQLite is used for run history (structured queries).
- Pro access is gated via `useProAccess` hook and `ProGate` component. Swap the stub implementation with RevenueCat or react-native-iap when billing is ready.
- All scoring functions are pure and testable — see `services/scoring.ts`.

---

## License

Private / Proprietary. All rights reserved.
