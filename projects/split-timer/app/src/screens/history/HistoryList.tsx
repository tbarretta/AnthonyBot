/**
 * HistoryList.tsx
 * Scrollable list of past runs, sorted by date. Shows label, total time, shot count.
 * Navigates to RunDetail.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function HistoryListScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>HistoryList</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
