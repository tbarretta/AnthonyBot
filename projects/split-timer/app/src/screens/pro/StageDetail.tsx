/**
 * StageDetail.tsx
 * Pro: Stage detail — all runs on this stage, best/average hit factor.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function StageDetailScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>StageDetail</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
