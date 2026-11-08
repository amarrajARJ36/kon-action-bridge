"use client";

import React from "react";
import { Bot, Sparkles, Mic, Volume2 } from "lucide-react";

export interface AvatarStateProps {
  isSpeaking?: boolean;
  isListening?: boolean;
  isThinking?: boolean;
  avatarName?: string;
  avatarRole?: string;
}

export function AvatarPlaceholder({
  isSpeaking = false,
  isListening = false,
  isThinking = false,
  avatarName = "KON Shopping Assistant",
  avatarRole = "Conversational AI Governance Bridge",
}: AvatarStateProps) {
  let ringStyle = "border-[#00e575] shadow-[#00e575]/20";
  let statusText = "Ready to assist";
  let badgeClass = "bg-emerald-50 text-[#008239] border-emerald-200";

  if (isListening) {
    ringStyle = "border-[#00e575] shadow-[#00e575]/40 animate-pulse ring-4 ring-[#00e575]/25";
    statusText = "Listening to your voice...";
    badgeClass = "bg-[#00e575]/20 text-[#004724] border-[#00e575]";
  } else if (isThinking) {
    ringStyle = "border-[#ffb800] shadow-amber-200 animate-pulse ring-4 ring-amber-300/30";
    statusText = "Processing...";
    badgeClass = "bg-amber-50 text-amber-800 border-amber-300";
  } else if (isSpeaking) {
    ringStyle = "border-[#00e575] shadow-emerald-200";
    statusText = "Speaking response...";
    badgeClass = "bg-emerald-100 text-[#004724] border-emerald-400";
  }

  return (
    <div
      data-avatar-placeholder="kon-digital-human"
      className="flex flex-col items-center justify-center p-3.5 bg-gradient-to-b from-emerald-50/70 via-white to-white rounded-2xl border border-emerald-100 shadow-sm"
    >
      <div className="relative">
        {/* Animated ring */}
        <div
          className={`w-20 h-20 sm:w-22 sm:h-22 rounded-full border-2 ${ringStyle} p-1 flex items-center justify-center shadow-md transition-all duration-300 bg-white`}
        >
          {/* Avatar Graphic */}
          <div className="w-full h-full rounded-full bg-gradient-to-tr from-[#004724] via-[#008239] to-[#00e575] flex flex-col items-center justify-center relative overflow-hidden group">
            <Bot className="w-10 h-10 text-white drop-shadow-md transition-transform group-hover:scale-105" />

            {/* Gemini Live Mode Animated Waveform */}
            {(isSpeaking || isListening) && (
              <div className="absolute inset-x-0 bottom-1.5 flex justify-center items-end gap-1 px-3 h-5">
                <span className="w-1 bg-[#00e575] rounded-full animate-[bounce_0.8s_infinite_-0.4s] h-2.5" />
                <span className="w-1 bg-white rounded-full animate-[bounce_0.8s_infinite_-0.2s] h-4" />
                <span className="w-1.5 bg-[#00e575] rounded-full animate-[bounce_0.8s_infinite] h-5" />
                <span className="w-1 bg-white rounded-full animate-[bounce_0.8s_infinite_-0.3s] h-4" />
                <span className="w-1 bg-[#00e575] rounded-full animate-[bounce_0.8s_infinite_-0.1s] h-2.5" />
              </div>
            )}
          </div>
        </div>

        {/* State Badge Icon */}
        <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-white border border-gray-200 shadow-md">
          {isListening ? (
            <Mic className="w-3.5 h-3.5 text-[#00b853] animate-pulse" />
          ) : isSpeaking ? (
            <Volume2 className="w-3.5 h-3.5 text-[#008239]" />
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-[#00e575]" />
          )}
        </div>
      </div>

      <div className="mt-2.5 text-center">
        <h3 className="text-sm font-extrabold text-gray-900 tracking-tight">{avatarName}</h3>
        <p className="text-[11px] text-gray-500 mt-0.5">{avatarRole}</p>
        <div className="mt-1.5 inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full border text-[10px] font-bold tracking-wide transition-colors">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isListening ? "bg-[#00e575] animate-ping" : isThinking ? "bg-[#ffb800] animate-ping" : "bg-[#00b853]"
            }`}
          />
          <span className={badgeClass.split(" ")[1]}>{statusText}</span>
        </div>
        <p className="text-[9px] text-gray-400 mt-1.5 font-medium italic">
          UI avatar placeholder • Uses speech synthesis & text fallback
        </p>
      </div>
    </div>
  );
}
