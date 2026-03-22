/**
 * EditRun.tsx
 * Edit label, notes, and scoring for a saved run.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function EditRunScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>EditRun</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
