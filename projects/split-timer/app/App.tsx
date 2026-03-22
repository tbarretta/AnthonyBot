import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Text } from 'react-native';

// Screen imports — placeholder implementations loaded from src/screens
import TimerHomeScreen from './src/screens/timer/TimerHome';
import TimerReadyScreen from './src/screens/timer/TimerReady';
import TimerRunningScreen from './src/screens/timer/TimerRunning';
import RunReviewScreen from './src/screens/timer/RunReview';
import SaveRunScreen from './src/screens/timer/SaveRun';
import HistoryListScreen from './src/screens/history/HistoryList';
import RunDetailScreen from './src/screens/history/RunDetail';
import EditRunScreen from './src/screens/history/EditRun';
import StatsOverviewScreen from './src/screens/stats/StatsOverview';
import SettingsHomeScreen from './src/screens/settings/SettingsHome';
import AppearanceScreen from './src/screens/settings/Appearance';
import AudioSettingsScreen from './src/screens/settings/AudioSettings';
import StartSignalScreen from './src/screens/settings/StartSignal';
import ParTimeScreen from './src/screens/settings/ParTime';
import SubscriptionScreen from './src/screens/settings/Subscription';
import AboutScreen from './src/screens/settings/About';

const Tab = createBottomTabNavigator();
const TimerStack = createStackNavigator();
const HistoryStack = createStackNavigator();
const SettingsStack = createStackNavigator();

function TimerStackNav() {
  return (
    <TimerStack.Navigator screenOptions={{ headerShown: false }}>
      <TimerStack.Screen name="TimerHome" component={TimerHomeScreen} />
      <TimerStack.Screen name="TimerReady" component={TimerReadyScreen} />
      <TimerStack.Screen name="TimerRunning" component={TimerRunningScreen} />
      <TimerStack.Screen name="RunReview" component={RunReviewScreen} />
      <TimerStack.Screen name="SaveRun" component={SaveRunScreen} />
    </TimerStack.Navigator>
  );
}

function HistoryStackNav() {
  return (
    <HistoryStack.Navigator screenOptions={{ headerShown: false }}>
      <HistoryStack.Screen name="HistoryList" component={HistoryListScreen} />
      <HistoryStack.Screen name="RunDetail" component={RunDetailScreen} />
      <HistoryStack.Screen name="EditRun" component={EditRunScreen} />
    </HistoryStack.Navigator>
  );
}

function SettingsStackNav() {
  return (
    <SettingsStack.Navigator screenOptions={{ headerShown: false }}>
      <SettingsStack.Screen name="SettingsHome" component={SettingsHomeScreen} />
      <SettingsStack.Screen name="Appearance" component={AppearanceScreen} />
      <SettingsStack.Screen name="AudioSettings" component={AudioSettingsScreen} />
      <SettingsStack.Screen name="StartSignal" component={StartSignalScreen} />
      <SettingsStack.Screen name="ParTime" component={ParTimeScreen} />
      <SettingsStack.Screen name="Subscription" component={SubscriptionScreen} />
      <SettingsStack.Screen name="About" component={AboutScreen} />
    </SettingsStack.Navigator>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <Tab.Navigator
          screenOptions={{
            headerShown: false,
            tabBarStyle: { backgroundColor: '#1a1a1a', borderTopColor: '#2a2a2a' },
            tabBarActiveTintColor: '#f5a623',
            tabBarInactiveTintColor: '#555',
          }}
        >
          <Tab.Screen
            name="Timer"
            component={TimerStackNav}
            options={{
              tabBarLabel: 'TIMER',
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 16, color }}>⏱</Text>,
            }}
          />
          <Tab.Screen
            name="History"
            component={HistoryStackNav}
            options={{
              tabBarLabel: 'HISTORY',
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 16, color }}>📋</Text>,
            }}
          />
          <Tab.Screen
            name="Stats"
            component={StatsOverviewScreen}
            options={{
              tabBarLabel: 'STATS',
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 16, color }}>📊</Text>,
            }}
          />
          <Tab.Screen
            name="Settings"
            component={SettingsStackNav}
            options={{
              tabBarLabel: 'SETTINGS',
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 16, color }}>⚙️</Text>,
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
