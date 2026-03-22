/**
 * AudioSettings.tsx
 * Audio detection configuration. Sensitivity, frequency range, min shot interval.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function AudioSettingsScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>AudioSettings</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
