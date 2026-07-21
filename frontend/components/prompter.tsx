import React from "react";
import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface PrompterProps {
  input: string;
  setInput: (text: string) => void;
  isLoading: boolean;
  handleGen: () => void;
}

export default function Prompter({
  input,
  setInput,
  isLoading,
  handleGen,
}: PrompterProps) {
  return (
    <View style={styles.container}>
      <View style={styles.inputWrapper}>
        <TextInput
          style={styles.input}
          placeholder="Ask Kaito..."
          placeholderTextColor="#52525B"
          value={input}
          onChangeText={setInput}
          multiline
          maxLength={1000}
        />
        {input.trim().length > 0 && (
          <TouchableOpacity
            style={[styles.sendButton, isLoading && styles.sendButtonDisabled]}
            disabled={isLoading}
            onPress={handleGen}
          >
            {isLoading ? (
              <ActivityIndicator size="small" color="#18181B" />
            ) : (
              <Ionicons name="arrow-forward-outline" size={20} color="#18181B" />
            )}
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingLeft: 8,
    paddingVertical: 12,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "flex-end",
    backgroundColor: "#18181B",
    borderColor: "#27272A",
    borderWidth: 1,
    borderRadius: 24,
    paddingVertical: 8,
    paddingHorizontal: 12,
    minHeight: 52,
  },
  input: {
    flex: 1,
    color: "#F4F4F5",
    fontSize: 16,
    paddingHorizontal: 10,
    paddingTop: 10,
    paddingBottom: 10,
    maxHeight: 120,
    textAlignVertical: "top",
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#F4F4F5",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 2,
    marginLeft: 8,
  },
  sendButtonDisabled: {
    backgroundColor: "#3F3F46",
    opacity: 0.5,
  },
});
