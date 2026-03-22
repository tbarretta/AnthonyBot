/**
 * RunDetail.tsx
 * Detailed view of a single run. Shows full split breakdown, scoring, and export options.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function RunDetailScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>RunDetail</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
