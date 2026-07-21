import React, { useState, useRef, useEffect } from "react";
import {
  Text,
  View,
  StyleSheet,
  ScrollView,
  Platform,
  Alert,
  TouchableOpacity,
  ActivityIndicator,
  Animated, // Import Animated for the pulsing effect
} from "react-native";
import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system/legacy";
import { Ionicons } from "@expo/vector-icons";
import Header from "../components/head";
import Prompter from "../components/prompter";
import { useKeyboardHeight } from "@/hooks/useKeyboardHeight";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  audioUri?: string;
  isThinking?: boolean; // New flag to identify the thinking state
}

export default function InterfacePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const recordingStartTime = useRef<number>(0);

  // Animation value for the "Thinking..." text
  const fadeAnim = useRef(new Animated.Value(0.4)).current;

  const scrollViewRef = useRef<ScrollView>(null);
  const keyboardHeight = useKeyboardHeight();
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);

  const API_URL = "http://192.168.0.111:8000/gen/";

  // Setup pulsing animation for "Thinking" state
  useEffect(() => {
    if (isLoading) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(fadeAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(fadeAnim, {
            toValue: 0.4,
            duration: 800,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    } else {
      fadeAnim.setValue(0.4); // Reset
    }
  }, [isLoading]);

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Microphone permission is required.");
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });
    })();

    return () => {
      if (soundRef.current) soundRef.current.unloadAsync();
      if (recordingRef.current) recordingRef.current.stopAndUnloadAsync();
    };
  }, []);

  const saveAudioFile = async (base64Data: string, messageId: string) => {
    try {
      if (!FileSystem.documentDirectory) return null;
      const fileUri = `${FileSystem.documentDirectory}voice_${messageId}.mp3`;
      await FileSystem.writeAsStringAsync(fileUri, base64Data, {
        encoding: FileSystem.EncodingType.Base64,
      });
      return fileUri;
    } catch (e) {
      console.error("Error saving audio file:", e);
      return null;
    }
  };

  const handleAudioToggle = async (msg: Message) => {
    try {
      // If clicking the same message that is playing, STOP it.
      if (playingMessageId === msg.id) {
        if (soundRef.current) {
          await soundRef.current.stopAsync();
          await soundRef.current.unloadAsync();
          soundRef.current = null;
        }
        setPlayingMessageId(null);
        return;
      }

      // If clicking a new message, stop the previous one first.
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }

      if (!msg.audioUri) return;

      const { sound } = await Audio.Sound.createAsync(
        { uri: msg.audioUri },
        { shouldPlay: true },
      );

      soundRef.current = sound;
      setPlayingMessageId(msg.id);

      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setPlayingMessageId(null);
          soundRef.current = null;
        }
      });
    } catch (error) {
      console.error("Audio Playback Error:", error);
      setPlayingMessageId(null);
    }
  };

  const startRecording = async () => {
    try {
      if (recordingRef.current) return;
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      recordingStartTime.current = Date.now();
      setIsRecording(true);
    } catch (err) {
      console.error("Failed to start recording", err);
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    const duration = Date.now() - recordingStartTime.current;
    setIsRecording(false);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (duration < 800) {
        console.log("Recording too short, discarding.");
        return;
      }
      if (uri) handleVoiceSend(uri);
    } catch (error) {
      console.log("Error stopping recording:", error);
      recordingRef.current = null;
    }
  };

  const handleVoiceSend = async (uri: string) => {
    setIsLoading(true);
    const tempId = Date.now().toString();
    const thinkingId = "thinking-" + tempId;

    // Add temporary voice msg AND thinking bubble
    setMessages((prev) => [
      ...prev,
      { id: tempId, text: "🎤 Sending Voice...", sender: "user" },
      { id: thinkingId, text: "Thinking...", sender: "bot", isThinking: true },
    ]);

    try {
      const formData = new FormData();
      // @ts-ignore
      formData.append("audio", {
        uri: Platform.OS === "android" ? uri : uri.replace("file://", ""),
        name: "voice.wav",
        type: "audio/wav",
      });

      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "multipart/form-data" },
        body: formData,
      });

      const data = await response.json();
      processResponse(data, tempId, true, thinkingId);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Failed to send audio.");
      // Remove the thinking bubble if error
      setMessages((prev) =>
        prev.filter((m) => m.id !== thinkingId && m.id !== tempId),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextSend = async () => {
    if (!input.trim()) return;

    const promptToSend = input;
    const tempId = Date.now().toString();
    const thinkingId = "thinking-" + tempId;

    setInput("");
    setIsLoading(true);

    // Add User Msg AND Thinking Bubble immediately
    setMessages((prev) => [
      ...prev,
      { id: tempId, text: promptToSend, sender: "user" },
      { id: thinkingId, text: "Thinking...", sender: "bot", isThinking: true },
    ]);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptToSend }),
      });

      const data = await response.json();
      processResponse(data, null, false, thinkingId);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Connection failed.");
      setMessages((prev) => prev.filter((m) => m.id !== thinkingId)); // Remove thinking on error
    } finally {
      setIsLoading(false);
    }
  };

  const processResponse = async (
    data: any,
    tempId: string | null,
    isVoice: boolean,
    thinkingId: string,
  ) => {
    // 1. Update the user's temporary "Sending..." message if it was voice
    if (tempId && isVoice) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId ? { ...m, text: "🎤 Voice Command" } : m,
        ),
      );
    }

    // 2. Process Bot Response
    if (data.reply) {
      const botMsgId = (Date.now() + 1).toString();
      let audioUri = undefined;

      if (data.audio) {
        const savedUri = await saveAudioFile(data.audio, botMsgId);
        if (savedUri) audioUri = savedUri;
      }

      const botMsg: Message = {
        id: botMsgId,
        text: data.reply,
        sender: "bot",
        audioUri: audioUri,
        isThinking: false,
      };

      // 3. REPLACE the "Thinking..." bubble with the real message
      setMessages((prev) =>
        prev.map((msg) => (msg.id === thinkingId ? botMsg : msg)),
      );

      // Optional: Uncomment below to Auto-play audio when received
      // if (audioUri) handleAudioToggle(botMsg);
    }
  };

  return (
    <View style={styles.container}>
      <Header />

      <ScrollView
        ref={scrollViewRef}
        style={styles.chatContainer}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() =>
          scrollViewRef.current?.scrollToEnd({ animated: true })
        }
        keyboardDismissMode="on-drag"
      >
        {messages.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateTitle}>Kaito AI</Text>
            <Text style={styles.emptyStateSubtitle}>Voice & Text Enabled</Text>
          </View>
        ) : (
          messages.map((msg) => (
            <View
              key={msg.id}
              style={[
                styles.bubble,
                msg.sender === "user" ? styles.userBubble : styles.botBubble,
              ]}
            >
              <View style={styles.bubbleContent}>
                {msg.isThinking ? (
                  <View style={{ flexDirection: "row", alignItems: "center" }}>
                    <ActivityIndicator
                      size="small"
                      color="#A1A1AA"
                      style={{ marginRight: 8 }}
                    />
                    <Animated.Text
                      style={[
                        styles.botText,
                        { opacity: fadeAnim, fontStyle: "italic" },
                      ]}
                    >
                      {msg.text}
                    </Animated.Text>
                  </View>
                ) : (
                  <Text
                    style={
                      msg.sender === "user" ? styles.userText : styles.botText
                    }
                  >
                    {msg.text}
                  </Text>
                )}
                {msg.sender === "bot" && !msg.isThinking && msg.audioUri && (
                  <TouchableOpacity
                    onPress={() => handleAudioToggle(msg)}
                    style={styles.speakerIcon}
                    // hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                  >
                    <Ionicons
                      name={
                        playingMessageId === msg.id
                          ? "stop-circle"
                          : "volume-medium"
                      }
                      size={24}
                      color={
                        playingMessageId === msg.id ? "#ef4444" : "#A1A1AA"
                      }
                    />
                  </TouchableOpacity>
                )}

              </View>
            </View>
          ))
        )}
      </ScrollView>

      <View
        style={[
          styles.prompterWrapper,
          { paddingBottom: keyboardHeight > 0 ? 30 : 30 },
        ]}
      >
        <View style={styles.inputContainer}>
          <Prompter
            input={input}
            setInput={setInput}
            isLoading={isLoading}
            handleGen={handleTextSend}
          />

          <TouchableOpacity
            style={[styles.micButton, isRecording && styles.micButtonActive]}
            activeOpacity={0.7}
            onPressIn={startRecording}
            onPressOut={stopRecording}
            disabled={isLoading}
          >
            <Ionicons
              name={isRecording ? "mic" : "mic-outline"}
              size={24}
              color={isLoading ? "#52525b" : "#F4F4F5"}
            />
          </TouchableOpacity>
        </View>
      </View>
      <View style={{ height: keyboardHeight }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#09090b" },
  chatContainer: { flex: 1 },
  chatContent: { padding: 20, paddingBottom: 40, flexGrow: 1 },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 100,
    opacity: 0.5,
  },
  emptyStateTitle: {
    color: "#F4F4F5",
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 8,
  },
  emptyStateSubtitle: { color: "#A1A1AA", fontSize: 14 },
  bubble: { padding: 14, borderRadius: 18, marginVertical: 6, maxWidth: "85%" },
  bubbleContent: {
    flexDirection: "column",
    alignItems: "flex-end",
    justifyContent: "space-between",
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#27272A",
    borderBottomRightRadius: 4,
  },
  botBubble: {
    alignSelf: "flex-start",
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#27272A",
    borderBottomLeftRadius: 4,
    minWidth: 120,
  },
  userText: { color: "#F4F4F5", fontSize: 16, lineHeight: 22 },
  botText: { color: "#D4D4D8", fontSize: 16, lineHeight: 22 },
  speakerIcon: {
    marginLeft: 10,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 10,
  },
  micButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#27272A",
    justifyContent: "center",
    alignItems: "center",
  },
  prompterWrapper: {
    width: "100%",
    alignItems: "center",
    backgroundColor: "#09090b",
  },
  micButtonActive: { backgroundColor: "#DC2626", transform: [{ scale: 1.1 }] },
});
