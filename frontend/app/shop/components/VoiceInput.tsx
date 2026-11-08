"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, AlertCircle } from "lucide-react";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  onListeningChange?: (listening: boolean) => void;
}

export function VoiceInput({ onTranscript, disabled = false, onListeningChange }: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [hasSupport, setHasSupport] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setHasSupport(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
        setErrorMessage(null);
        onListeningChange?.(true);
      };

      recognition.onresult = (event: any) => {
        let transcript = event.results[0][0].transcript;
        if (transcript) {
          // Clean speech-to-text phonetic homophones for grocery shopping
          transcript = transcript
            .replace(/\b(at court|in court|to court|at caught|to card|to caught)\b/gi, "to cart")
            .replace(/\b(you had to cut|had to cut|you have to cut)\b/gi, "add")
            .replace(/\bcut\s+(one|a|an|two|\d+)/gi, "add $1")
            .replace(/\b(pomegranate|pomegranets)\b/gi, "pomegranates");

          onTranscript(transcript);
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        onListeningChange?.(false);
        if (event.error === "not-allowed") {
          setErrorMessage("Mic blocked. Please allow microphone permissions in your browser.");
        } else if (event.error === "no-speech") {
          setErrorMessage("No speech detected. Please speak clearly into the mic.");
        } else {
          setErrorMessage(`Mic notice: ${event.error}`);
        }
        setTimeout(() => setErrorMessage(null), 5000);
      };

      recognition.onend = () => {
        setIsListening(false);
        onListeningChange?.(false);
      };

      recognitionRef.current = recognition;
    } catch (e) {
      setHasSupport(false);
    }
  }, [onTranscript, onListeningChange]);

  const toggleListening = () => {
    if (disabled) return;

    if (!hasSupport) {
      setErrorMessage("Browser voice API not available. Type your message or click prompt chips.");
      setTimeout(() => setErrorMessage(null), 4000);
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch (err) {
        setIsListening(false);
      }
    } else {
      setErrorMessage(null);
      try {
        recognitionRef.current?.start();
      } catch (err) {
        console.warn("Speech recognition start:", err);
      }
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        aria-label={isListening ? "Stop listening" : "Start speaking voice request"}
        title={isListening ? "Listening... click to send" : "Tap to speak grocery request"}
        className={`p-2.5 sm:p-3 rounded-full border transition-all flex items-center justify-center ${
          isListening
            ? "bg-[#00e575] text-[#09281a] border-[#00b853] shadow-lg shadow-emerald-500/40 animate-pulse ring-4 ring-[#00e575]/30"
            : "bg-white hover:bg-emerald-50 text-gray-700 hover:text-[#008239] border-gray-300 hover:border-[#00e575] shadow-xs"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <Mic className={`w-5 h-5 ${isListening ? "animate-bounce" : ""}`} />
      </button>

      {errorMessage && (
        <div className="absolute bottom-14 right-0 w-64 p-2.5 bg-gray-900 text-white text-xs rounded-xl shadow-2xl flex items-start gap-2 z-50 animate-fade-in border border-gray-700">
          <AlertCircle className="w-4 h-4 text-[#ffb800] shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
