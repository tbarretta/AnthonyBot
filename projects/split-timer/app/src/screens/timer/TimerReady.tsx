/**
 * TimerReady.tsx
 * Pre-start screen. Shows par time config, plays countdown beep sequence with
 * random delay, then transitions to TimerRunning.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function TimerReadyScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>TimerReady</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
