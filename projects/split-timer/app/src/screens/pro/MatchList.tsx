/**
 * MatchList.tsx
 * Pro: List of all matches. Navigate to MatchDetail.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function MatchListScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>MatchList</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
