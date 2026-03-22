/**
 * TimerRunning.tsx
 * Active timer screen. Displays elapsed time, shot count, and split times in real time.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function TimerRunningScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>TimerRunning</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
