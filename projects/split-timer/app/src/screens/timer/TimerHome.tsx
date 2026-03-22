/**
 * TimerHome.tsx
 * Entry point for the Timer tab. Shows current input mode and a large START button.
 * Navigates to InputModeSelect or directly to TimerReady.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function TimerHomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>TimerHome</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
