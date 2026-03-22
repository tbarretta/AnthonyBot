/**
 * ParTime.tsx
 * Par time configuration screen. Set par time target in seconds.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function ParTimeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>ParTime</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111', alignItems: 'center', justifyContent: 'center' },
  text: { color: '#fff', fontSize: 16 },
});
