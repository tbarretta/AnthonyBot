/**
 * MatchDetail.tsx
 * Pro: Match overview — all stages, aggregate results.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function MatchDetailScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>MatchDetail</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
