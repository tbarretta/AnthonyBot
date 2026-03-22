/**
 * RunReview.tsx
 * Post-run review screen. Shows split breakdown and scoring options.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function RunReviewScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>RunReview</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
