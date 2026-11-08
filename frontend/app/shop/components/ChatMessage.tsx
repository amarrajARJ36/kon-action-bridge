"use client";

import React from "react";
import { User as UserIcon, Bot } from "lucide-react";
import { ChatMessage as ChatMessageType, Product } from "@/lib/types";
import { ProductCard } from "./ProductCard";

interface ChatMessageProps {
  message: ChatMessageType;
  onSelectProduct?: (productId: string, quantity: number) => void;
  isAddingProduct?: boolean;
}

export function ChatMessage({ message, onSelectProduct, isAddingProduct = false }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div className={`flex gap-2.5 mb-3.5 animate-fade-in ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Assistant Avatar Icon */}
      {isAssistant && (
        <div className="w-8 h-8 rounded-full bg-[#004724] flex items-center justify-center text-white shrink-0 shadow-xs mt-0.5 border border-emerald-500/30">
          <Bot className="w-4 h-4 text-[#00e575]" />
        </div>
      )}

      <div className={`max-w-[88%] sm:max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Message bubble */}
        <div
          className={`rounded-2xl px-3.5 py-2.5 text-xs sm:text-sm leading-relaxed shadow-xs ${
            isUser
              ? "bg-[#00e575] text-[#09281a] font-semibold rounded-br-xs"
              : message.message_type === "error"
              ? "bg-rose-50 text-rose-800 border border-rose-200 rounded-bl-xs"
              : "bg-white text-gray-800 border border-gray-200 rounded-bl-xs shadow-xs"
          }`}
        >
          {message.content}
        </div>

        {/* Product options clarification cards */}
        {message.products_to_select && message.products_to_select.length > 0 && onSelectProduct && (
          <div className="mt-2.5">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">
              Select product option:
            </p>
            <div className="flex gap-2.5 overflow-x-auto pb-2 pt-0.5 scrollbar-thin">
              {message.products_to_select.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onSelect={onSelectProduct}
                  isAdding={isAddingProduct}
                />
              ))}
            </div>
          </div>
        )}

        <div className={`mt-1 text-[10px] text-gray-400 px-1 ${isUser ? "text-right" : "text-left"}`}>
          {message.timestamp}
        </div>
      </div>

      {/* User Icon */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-emerald-100 border border-emerald-300 flex items-center justify-center text-[#004724] shrink-0 mt-0.5">
          <UserIcon className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
