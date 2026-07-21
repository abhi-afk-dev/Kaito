import React, { useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Easing,
  TouchableOpacity,
  Platform,
  Modal,
  Pressable,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

const Header = () => {
  const [showSettingsOverlay, setShowSettingsOverlay] = useState(false);
  const rotateAnim = useRef(new Animated.Value(0)).current;

  const handleSettingsPress = () => {
    const isOverlayOpen = !showSettingsOverlay;
    setShowSettingsOverlay(isOverlayOpen);
    Animated.timing(rotateAnim, {
      toValue: isOverlayOpen ? 1 : 0,
      duration: 200,
      easing: Easing.linear,
      useNativeDriver: true,
    }).start();
  };

  const closeSettings = () => {
    setShowSettingsOverlay(false);
    Animated.timing(rotateAnim, {
      toValue: 0,
      duration: 200,
      easing: Easing.linear,
      useNativeDriver: true,
    }).start();
  };

  const rotateInterpolate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "-90deg"],
  });

  const animatedStyle = {
    transform: [{ rotate: rotateInterpolate }],
  };

  return (
    <SafeAreaView edges={["top"]} style={styles.safeArea}>
      <View style={styles.header}>
        <View style={styles.headerTitleContainer}>
          <Text style={styles.logoSymbol}>盗</Text>
        </View>

        <TouchableOpacity
          onPress={handleSettingsPress}
          style={styles.iconButton}
        >
          <Animated.View style={animatedStyle}>
            <Ionicons name="settings-outline" size={24} color="#A1A1AA" />
          </Animated.View>
        </TouchableOpacity>
      </View>

      <Modal
        transparent={true}
        visible={showSettingsOverlay}
        animationType="fade"
        onRequestClose={closeSettings}
      >
        <Pressable style={styles.overlayBackground} onPress={closeSettings}>
          <View style={styles.settingsOverlay}>
            {["Account", "Connect MCPs", "Log Out"].map((item, index) => (
              <React.Fragment key={item}>
                <TouchableOpacity style={styles.overlayOption}>
                  <Text style={styles.overlayText}>{item}</Text>
                </TouchableOpacity>
                {index < 2 && <View style={styles.overlaySeparator} />}
              </React.Fragment>
            ))}
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
};

export default Header;

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#09090b", // Zinc-950
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#27272A", // Zinc-800
    backgroundColor: "#09090b",
  },
  headerTitleContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  logoSymbol: {
    color: "#F4F4F5", // Zinc-100
    fontSize: 28,
    fontWeight: "600",
  },
  logoText: {
    color: "#E4E4E7", // Zinc-200
    fontSize: 20,
    fontWeight: "500",
    letterSpacing: 0.5,
  },
  iconButton: {
    padding: 4,
  },
  overlayBackground: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    justifyContent: "center",
    alignItems: "center",
  },
  settingsOverlay: {
    width: "70%",
    backgroundColor: "#18181B", // Zinc-900
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: "#27272A",
    alignItems: "center",
  },
  overlayOption: {
    width: "100%",
    paddingVertical: 16,
    alignItems: "center",
  },
  overlayText: {
    fontSize: 16,
    color: "#E4E4E7",
    fontWeight: "500",
  },
  overlaySeparator: {
    height: 1,
    width: "100%",
    backgroundColor: "#27272A",
  },
});
