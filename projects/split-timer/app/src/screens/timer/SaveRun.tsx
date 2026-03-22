/**
 * SaveRun.tsx
 * Save run screen. Allows user to label and add notes before persisting to storage.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function SaveRunScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>SaveRun</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
