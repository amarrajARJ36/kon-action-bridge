"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Search,
  ShoppingCart,
  Sparkles,
  Bot,
  Volume2,
  VolumeX,
  X,
  Send,
  Plus,
  Minus,
  Check,
  Star,
  Wheat,
  Drumstick,
  Apple,
  Egg,
  Milk,
  Droplet,
  Package,
  Zap,
  MapPin,
  Mic,
  Clock,
  ChevronDown,
  ArrowRight,
  ShieldCheck,
  Flame,
} from "lucide-react";
import {
  ChatMessage as ChatMessageType,
  CartResponse,
  Product,
} from "@/lib/types";
import {
  addToCart,
  confirmAssistantSelection,
  getCart,
  login,
  searchProducts,
  sendMessage,
} from "@/lib/api";
import { getSessionId, getToken, setToken } from "@/lib/auth";
import { AvatarPlaceholder } from "./components/AvatarPlaceholder";
import { VoiceInput } from "./components/VoiceInput";
import { ChatMessage } from "./components/ChatMessage";
import { BasketPanel } from "./components/BasketPanel";

// Guaranteed default seeded catalog so products display instantly with zero delay
const DEFAULT_PRODUCTS: Product[] = [
  {
    id: "11111111-1111-1111-1111-111111111101",
    sku: "ATTA-ALBAKER-01",
    name: "Al Baker Chakki Atta",
    brand: "Al Baker",
    category: "Atta",
    variant: "Chakki Fresh Atta",
    unit_of_measurement: "kg",
    price_aed: 8.5,
    stock_quantity: 200.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1509440159596-0249088772ff",
  },
  {
    id: "11111111-1111-1111-1111-111111111102",
    sku: "ATTA-AASHIRVAAD-01",
    name: "Aashirvaad Chakki Atta",
    brand: "Aashirvaad",
    category: "Atta",
    variant: "Chakki Fresh Atta",
    unit_of_measurement: "kg",
    price_aed: 12.0,
    stock_quantity: 150.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1509440159596-0249088772ff",
  },
  {
    id: "11111111-1111-1111-1111-111111111103",
    sku: "ATTA-HOUSE-01",
    name: "Whole Wheat Atta (Generic)",
    brand: "House Brand",
    category: "Atta",
    variant: "Whole Wheat",
    unit_of_measurement: "kg",
    price_aed: 5.75,
    stock_quantity: 300.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1509440159596-0249088772ff",
  },
  {
    id: "22222222-2222-2222-2222-222222222201",
    sku: "BAN-REG-01",
    name: "Regular Bananas",
    brand: "Fresh Farms",
    category: "Bananas",
    variant: "Cavendish Bananas",
    unit_of_measurement: "kg",
    price_aed: 4.25,
    stock_quantity: 50.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
  },
  {
    id: "22222222-2222-2222-2222-222222222202",
    sku: "BAN-ORG-01",
    name: "Organic Bananas",
    brand: "Organic Valley",
    category: "Bananas",
    variant: "Organic Cavendish",
    unit_of_measurement: "kg",
    price_aed: 7.5,
    stock_quantity: 30.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
  },
  {
    id: "22222222-2222-2222-2222-222222222203",
    sku: "BAN-BABY-01",
    name: "Baby Bananas",
    brand: "Fresh Farms",
    category: "Bananas",
    variant: "Mini/Lady Finger Bananas",
    unit_of_measurement: "kg",
    price_aed: 9.0,
    stock_quantity: 20.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
  },
  {
    id: "33333333-3333-3333-3333-333333333301",
    sku: "CHK-WHOLE-01",
    name: "Whole Chicken",
    brand: "Al Rawdah",
    category: "Chicken",
    variant: "Fresh Whole Chicken",
    unit_of_measurement: "kg",
    price_aed: 22.0,
    stock_quantity: 100.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1587593810167-a84920ea0781",
  },
  {
    id: "33333333-3333-3333-3333-333333333302",
    sku: "CHK-BREAST-01",
    name: "Chicken Breast",
    brand: "Al Rawdah",
    category: "Chicken",
    variant: "Fresh Boneless Breast Fillet",
    unit_of_measurement: "kg",
    price_aed: 38.5,
    stock_quantity: 80.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
  },
  {
    id: "33333333-3333-3333-3333-333333333303",
    sku: "CHK-CUBES-01",
    name: "Boneless Chicken Cubes",
    brand: "Al Rawdah",
    category: "Chicken",
    variant: "Fresh Boneless Cubes",
    unit_of_measurement: "kg",
    price_aed: 35.0,
    stock_quantity: 60.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
  },
  {
    id: "33333333-3333-3333-3333-333333333304",
    sku: "CHK-THIGHS-01",
    name: "Chicken Thighs",
    brand: "Al Rawdah",
    category: "Chicken",
    variant: "Boneless Thigh Fillet",
    unit_of_measurement: "kg",
    price_aed: 32.0,
    stock_quantity: 70.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1604503468506-a8da13d82791",
  },
  {
    id: "44444444-4444-4444-4444-444444444401",
    sku: "RICE-DAAWAT-01",
    name: "Basmati Rice",
    brand: "Daawat",
    category: "Rice",
    variant: "Extra Long Basmati",
    unit_of_measurement: "kg",
    price_aed: 15.0,
    stock_quantity: 200.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1586201375761-83865001e31c",
  },
  {
    id: "44444444-4444-4444-4444-444444444402",
    sku: "RICE-ROZANA-01",
    name: "Sella Basmati Rice",
    brand: "Rozana",
    category: "Rice",
    variant: "Sella (Parboiled)",
    unit_of_measurement: "kg",
    price_aed: 11.5,
    stock_quantity: 180.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1586201375761-83865001e31c",
  },
  {
    id: "55555555-5555-5555-5555-555555555501",
    sku: "EGG-ALAIN-01",
    name: "Fresh Eggs (12 pack)",
    brand: "Al Ain Farms",
    category: "Eggs",
    variant: "Large White Eggs",
    unit_of_measurement: "pack",
    price_aed: 12.0,
    stock_quantity: 100.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f",
  },
  {
    id: "66666666-6666-6666-6666-666666666601",
    sku: "MILK-ALAIN-01",
    name: "Full Fat Milk 1L",
    brand: "Al Ain Farms",
    category: "Milk",
    variant: "Fresh Full Fat",
    unit_of_measurement: "litre",
    price_aed: 5.5,
    stock_quantity: 120.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1550583724-b2692b85b150",
  },
  {
    id: "66666666-6666-6666-6666-666666666602",
    sku: "MILK-ALMARAI-01",
    name: "Low Fat Milk 1L",
    brand: "Almarai",
    category: "Milk",
    variant: "Long Life Low Fat",
    unit_of_measurement: "litre",
    price_aed: 6.25,
    stock_quantity: 90.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1550583724-b2692b85b150",
  },
  {
    id: "77777777-7777-7777-7777-777777777701",
    sku: "OIL-RAHMA-01",
    name: "Extra Virgin Olive Oil 750ml",
    brand: "Rahma",
    category: "Olive Oil",
    variant: "Extra Virgin Cold Pressed",
    unit_of_measurement: "bottle",
    price_aed: 28.0,
    stock_quantity: 60.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5",
  },
  {
    id: "88888888-8888-8888-8888-888888888801",
    sku: "VEG-TOMATO-01",
    name: "Fresh Tomatoes",
    brand: "Local Farm",
    category: "Tomatoes",
    variant: "Round Tomatoes",
    unit_of_measurement: "kg",
    price_aed: 3.5,
    stock_quantity: 80.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1592924357228-91a4daadcfea",
  },
  {
    id: "99999999-9999-9999-9999-999999999901",
    sku: "FRT-APPLE-01",
    name: "Fresh Royal Gala Apples",
    brand: "Fresh Farms",
    category: "Fruits",
    variant: "Royal Gala Apples",
    unit_of_measurement: "kg",
    price_aed: 7.5,
    stock_quantity: 100.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6",
  },
  {
    id: "99999999-9999-9999-9999-999999999902",
    sku: "FRT-ORANGE-01",
    name: "Fresh Valencia Oranges",
    brand: "Citrus Valley",
    category: "Fruits",
    variant: "Valencia Oranges",
    unit_of_measurement: "kg",
    price_aed: 5.5,
    stock_quantity: 120.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1582979512210-99b6a53386f9",
  },
  {
    id: "99999999-9999-9999-9999-999999999903",
    sku: "FRT-POM-01",
    name: "Fresh Ruby Pomegranates",
    brand: "Organic Oasis",
    category: "Fruits",
    variant: "Ruby Red Pomegranates",
    unit_of_measurement: "kg",
    price_aed: 14.0,
    stock_quantity: 80.0,
    is_available: true,
    image_url: "https://images.unsplash.com/photo-1615485290382-441e4d049cb5",
  },
];

export default function CareemShopPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [products, setProducts] = useState<Product[]>(DEFAULT_PRODUCTS);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>(DEFAULT_PRODUCTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [cart, setCart] = useState<CartResponse | null>(null);

  // Pop-up modals
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);

  // AI Chat & Voice states
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isAddingProduct, setIsAddingProduct] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);

  // Track adding animation per product
  const [addingMap, setAddingMap] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Preload speech synthesis voices on mount
  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  useEffect(() => {
    const sId = getSessionId();
    setSessionId(sId);

    // Ensure authenticated session token for demo customer
    if (!getToken()) {
      login("demo_customer", "customer123")
        .then((authRes) => {
          setToken(authRes.access_token);
          getCart(sId).then((c) => setCart(c)).catch(() => null);
        })
        .catch((err) => console.warn("Auto-auth demo customer error:", err));
    } else {
      // Fetch initial cart
      getCart(sId)
        .then((c) => setCart(c))
        .catch(() => null);
    }

    // Initial greeting from KON Commerce AI Assistant
    setMessages([
      {
        id: "msg-welcome",
        role: "assistant",
        content:
          "Marhaba & Hello! I'm your KON Commerce AI Assistant. Say or type what you need (e.g. '2 kg of atta, 1 kg bananas and 1 kg chicken'), and I'll find the best groceries, clarify your preferences, and add them to your basket in seconds!",
        timestamp: "Just now",
        message_type: "text",
      },
    ]);

    // Fetch live products from backend
    searchProducts("", "", 50)
      .then((res) => {
        if (res?.products && res.products.length > 0) {
          setProducts(res.products);
          setFilteredProducts(res.products);
        }
      })
      .catch((err) => console.warn("Using default catalog fallback:", err));
  }, []);

  // Filter products by category & search query
  useEffect(() => {
    let list = [...products];

    if (selectedCategory !== "All") {
      const sel = selectedCategory.toLowerCase();
      list = list.filter((p) => {
        const cat = p.category.toLowerCase();
        if (sel === "atta") return cat.includes("atta") || cat.includes("flour");
        if (sel === "bananas") return cat.includes("banana") || cat.includes("fruit");
        if (sel === "chicken") return cat.includes("chicken") || cat.includes("meat");
        if (sel === "dairy") return cat.includes("milk") || cat.includes("egg") || cat.includes("dairy");
        if (sel === "rice") return cat.includes("rice") || cat.includes("grain");
        if (sel === "oils") return cat.includes("oil");
        return cat.includes(sel);
      });
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.brand.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q) ||
          (p.variant && p.variant.toLowerCase().includes(q))
      );
    }

    setFilteredProducts(list);
  }, [products, selectedCategory, searchQuery]);

  // Auto-scroll chat stream
  useEffect(() => {
    if (isAssistantOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, isAssistantOpen]);

  const refreshCart = async () => {
    try {
      const updated = await getCart(sessionId);
      setCart(updated);
    } catch (err) {
      console.warn("Could not refresh cart:", err);
    }
  };

  // Neural Audio Playback (Edge Neural Voices matching Gemini Live)
  const playNeuralAudio = (audioBase64: string, fallbackText: string) => {
    if (!ttsEnabled || typeof window === "undefined") return;

    try {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      }

      const audio = new Audio("data:audio/mp3;base64," + audioBase64);
      audioPlayerRef.current = audio;

      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => {
        setIsSpeaking(false);
        speakText(fallbackText);
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.warn("Audio autoplay blocked by browser policy, falling back to speech:", err);
          setIsSpeaking(false);
          speakText(fallbackText);
        });
      }
    } catch (err) {
      console.warn("Neural audio error:", err);
      speakText(fallbackText);
    }
  };

  const toggleTTS = () => {
    if (isSpeaking) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      }
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setIsSpeaking(false);
    }
    setTtsEnabled(!ttsEnabled);
  };

  // Text-To-Speech helper with expressive, high-clarity voice (Gemini Live feel)
  const speakText = (text: string) => {
    if (!ttsEnabled || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();

    // Format text naturally for speech
    const cleanText = text
      .replace(/AED\s*(\d+(?:\.\d+)?)/gi, "$1 Dirhams")
      .replace(/(\d+)\s*kg\b/gi, "$1 kilograms")
      .replace(/(\d+)\s*g\b/gi, "$1 grams")
      .replace(/[\*\#\_\[\]\(\)\<\>]/g, "")
      .replace(/Careem Quik/gi, "Careem Quick");

    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Pick the most human-like, expressive voice available
    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length > 0) {
      // Prioritize natural neural English voices (macOS Enhanced, Google, Natural)
      const preferred =
        voices.find(
          (v) =>
            (v.lang.startsWith("en") || v.lang.startsWith("en-US") || v.lang.startsWith("en-GB")) &&
            (v.name.includes("Natural") ||
              v.name.includes("Enhanced") ||
              v.name.includes("Premium") ||
              v.name.includes("Google") ||
              v.name.includes("Samantha") ||
              v.name.includes("Daniel") ||
              v.name.includes("Ava") ||
              v.name.includes("Karen") ||
              v.name.includes("Jenny"))
        ) || voices.find((v) => v.lang.startsWith("en"));

      if (preferred) {
        utterance.voice = preferred;
      }
    }

    // Dynamic, energetic conversational cadence like Gemini Live
    utterance.pitch = 1.05;
    utterance.rate = 1.04;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  // Send message to Conversational AI Agent
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputText).trim();
    if (!query || isLoading) return;

    setInputText("");
    setIsAssistantOpen(true);

    const userMsg: ChatMessageType = {
      id: "usr-" + Date.now(),
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await sendMessage(query, sessionId);

      const asstMsg: ChatMessageType = {
        id: "asst-" + Date.now(),
        role: "assistant",
        content: res.message,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        action_taken: res.action_taken || undefined,
        products_to_select: res.products_to_select || undefined,
        message_type: res.products_to_select ? "product_options" : "text",
      };

      setMessages((prev) => [...prev, asstMsg]);

      if (res.cart) {
        setCart(res.cart);
      } else if (res.basket_updated) {
        refreshCart();
      }

      if (res.audio_base64) {
        playNeuralAudio(res.audio_base64, res.message);
      } else {
        speakText(res.message);
      }
    } catch (err: any) {
      const errorDetail =
        err.response?.data?.detail || "Could not connect to the KON Action Bridge assistant.";
      setMessages((prev) => [
        ...prev,
        {
          id: "err-" + Date.now(),
          role: "assistant",
          content: `Error: ${errorDetail}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          message_type: "error",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Direct catalog "Add to Cart" button handler
  const handleDirectAddToCart = async (product: Product, qty: number = 1) => {
    setAddingMap((prev) => ({ ...prev, [product.id]: true }));
    try {
      const updated = await addToCart(product.id, qty, sessionId);
      setCart(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add product to basket.");
    } finally {
      setTimeout(() => {
        setAddingMap((prev) => ({ ...prev, [product.id]: false }));
      }, 1000);
    }
  };

  const categories = [
    { id: "All", name: "All Groceries", icon: Package },
    { id: "Atta", name: "Atta & Flours", icon: Wheat },
    { id: "Bananas", name: "Fresh Fruits & Bananas", icon: Apple },
    { id: "Chicken", name: "Fresh Chicken & Meat", icon: Drumstick },
    { id: "Dairy", name: "Dairy, Milk & Eggs", icon: Milk },
    { id: "Rice", name: "Basmati Rice", icon: Package },
    { id: "Oils", name: "Cooking Oils", icon: Droplet },
  ];

  const quickPrompts = [
    "2 kg atta, 1 kg bananas and 1 kg chicken",
    "I need 2 kg of atta",
    "Add fresh chicken breast",
    "Show me milk and eggs",
    "View basket",
  ];

  return (
    <div className="min-h-screen bg-[#f4f6f8] text-[#111827] flex flex-col font-sans selection:bg-[#00e575] selection:text-[#09281a]">
      {/* 1. KON Commerce Demo Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 h-16 sm:h-20 flex items-center justify-between gap-4">
          {/* KON Logo & Badge */}
          <div className="flex items-center gap-6 shrink-0">
            <Link href="/shop" className="flex items-center gap-2 group">
              <div className="w-10 h-10 rounded-2xl bg-[#00e575] flex items-center justify-center font-black text-2xl text-[#09281a] shadow-xs tracking-tighter">
                K
              </div>
              <div className="flex flex-col">
                <span className="font-black text-xl tracking-tight text-[#004724] leading-none">
                  KON
                </span>
                <span className="text-[11px] font-extrabold text-[#008239] tracking-wider uppercase flex items-center gap-1 mt-0.5">
                  <Zap className="w-3 h-3 fill-current text-[#00e575]" />
                  Commerce Demo
                </span>
              </div>
            </Link>

            {/* Governed Sandbox Location Pill */}
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-[#004724]">
              <MapPin className="w-3.5 h-3.5 text-[#008239]" />
              <span className="font-bold">Mock Catalogue • Dubai Catalog Data</span>
              <span className="text-[10px] text-[#008239] font-black uppercase ml-1 px-1.5 py-0.5 rounded-md bg-[#00e575] text-[#09281a]">
                GOVERNED
              </span>
            </div>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-xl relative">
            <div className="relative flex items-center">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search milk, atta, fresh chicken, bananas, rice, oil..."
                className="w-full bg-[#f4f6f8] text-gray-900 placeholder:text-gray-400 text-xs sm:text-sm pl-4 pr-10 py-2.5 sm:py-3 rounded-full border border-gray-200 focus:bg-white focus:outline-none focus:border-[#00e575] focus:ring-2 focus:ring-[#00e575]/30 transition-all shadow-inner"
              />
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3.5 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : (
                <Search className="w-4 h-4 text-[#008239] absolute right-3.5 pointer-events-none" />
              )}
            </div>
          </div>

          {/* Right Header CTAs */}
          <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
            {/* Pop-up AI Assistant Trigger Button */}
            <button
              type="button"
              onClick={() => setIsAssistantOpen(true)}
              className="flex items-center gap-2 py-2 px-3.5 sm:px-4 rounded-full bg-[#00e575] hover:bg-[#00b853] text-[#09281a] font-extrabold text-xs sm:text-sm shadow-md shadow-emerald-500/20 transition-all transform hover:scale-105"
              title="Pop up KON AI Shopping Assistant"
            >
              <Bot className="w-4 h-4 fill-current" />
              <span className="hidden sm:inline">Ask KON AI</span>
              <span className="sm:hidden">AI</span>
            </button>

            {/* Cart Trigger Button */}
            <button
              type="button"
              onClick={() => setIsCartOpen(true)}
              className="flex items-center gap-2 py-2 px-3 sm:px-3.5 rounded-full bg-[#004724] hover:bg-[#00381c] text-white transition-all shadow-xs"
            >
              <div className="relative">
                <ShoppingCart className="w-4 h-4 text-[#00e575]" />
                {cart && cart.item_count > 0 && (
                  <span className="absolute -top-2 -right-2 bg-[#00e575] text-[#09281a] text-[9px] font-black rounded-full w-4 h-4 flex items-center justify-center">
                    {cart.item_count}
                  </span>
                )}
              </div>
              <span className="hidden md:inline text-xs font-bold text-white">
                AED {cart?.subtotal_aed?.toFixed(2) || "0.00"}
              </span>
            </button>

            {/* Admin Console Link */}
            <Link
              href="/admin"
              className="hidden lg:flex items-center gap-1.5 py-2 px-3 rounded-full bg-slate-100 hover:bg-emerald-50 text-slate-700 hover:text-[#004724] text-xs font-bold border border-gray-200 transition-colors"
              title="Open Governance & Security Console"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-[#008239]" />
              <span>Admin</span>
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Categories Strip */}
      <nav className="bg-white border-b border-gray-200 sticky top-16 sm:top-20 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 overflow-x-auto flex items-center gap-2 py-2.5 scrollbar-none">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const isSelected = selectedCategory === cat.id;

            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all ${
                  isSelected
                    ? "bg-[#004724] text-white shadow-xs"
                    : "bg-gray-100 text-gray-700 hover:bg-emerald-50 hover:text-[#008239]"
                }`}
              >
                <Icon className="w-3.5 h-3.5 text-[#00e575]" />
                <span>{cat.name}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* 3. Main Store Container */}
      <main className="max-w-7xl mx-auto px-4 py-5 sm:py-7 flex-1 w-full space-y-6">
        {/* KON Commerce Hero Banner */}
        <div className="rounded-3xl overflow-hidden bg-gradient-to-r from-[#004724] via-[#006031] to-[#008239] text-white shadow-lg p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 relative">
          <div className="space-y-2 text-center md:text-left z-10 max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#00e575]/20 text-[#00e575] text-xs font-black uppercase tracking-wider border border-[#00e575]/30">
              <Zap className="w-3.5 h-3.5 fill-current" />
              <span>KON Commerce Demo • Action Bridge Architecture</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-black tracking-tight leading-tight">
              Enterprise Conversational AI Shopping
            </h1>
            <p className="text-xs sm:text-sm text-emerald-100 leading-relaxed">
              Mock grocery catalogue demonstrating how an enterprise conversational agent could interact with a retailer's commerce APIs through a governed tool layer.
            </p>
          </div>

          <div className="shrink-0 z-10 flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={() => setIsAssistantOpen(true)}
              className="flex items-center justify-center gap-2.5 py-3.5 px-6 rounded-2xl bg-[#00e575] hover:bg-[#00b853] text-[#09281a] font-black text-sm shadow-xl shadow-emerald-950/40 transition-transform hover:scale-105 uppercase tracking-wide"
            >
              <Mic className="w-4 h-4 fill-current" />
              <span>Talk to KON AI Assistant</span>
            </button>
          </div>

          {/* Decorative Glow */}
          <div className="absolute -right-10 -bottom-10 w-80 h-80 bg-[#00e575]/15 rounded-full blur-3xl pointer-events-none" />
        </div>

        {/* Catalog Section Header */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight flex items-center gap-2">
              <span>{selectedCategory === "All" ? "Fresh Quik Groceries" : selectedCategory}</span>
              <span className="text-xs font-bold text-[#008239] bg-emerald-100 px-2.5 py-0.5 rounded-full">
                ⚡ 15m Delivery
              </span>
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Showing {filteredProducts.length} items in AED • Sourced from certified UAE partners
            </p>
          </div>

          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="text-xs text-[#008239] font-bold hover:underline"
            >
              Clear filter
            </button>
          )}
        </div>

        {/* 4. Careem White Product Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3.5 sm:gap-4.5">
          {filteredProducts.map((product) => {
            const isAdding = addingMap[product.id] || false;
            const mrp = (product.price_aed * 1.25).toFixed(2);
            const discountPct = Math.round(((parseFloat(mrp) - product.price_aed) / parseFloat(mrp)) * 100);

            return (
              <div
                key={product.id}
                className="bg-white rounded-2xl border border-gray-200/80 hover:border-[#00e575] hover:shadow-xl transition-all duration-200 flex flex-col justify-between overflow-hidden group p-3.5"
              >
                {/* Product Image Area */}
                <div className="relative h-36 sm:h-44 bg-gray-50 rounded-xl overflow-hidden mb-3 flex items-center justify-center">
                  <span className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-[#004724] text-[#00e575] text-[10px] font-black uppercase tracking-wider flex items-center gap-1 shadow-xs">
                    <Zap className="w-2.5 h-2.5 fill-current" /> 15m
                  </span>

                  <span className="absolute top-2 right-2 z-10 px-1.5 py-0.5 rounded-md bg-amber-500 text-white text-[10px] font-black">
                    {discountPct}% OFF
                  </span>

                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                </div>

                {/* Product Details */}
                <div className="flex-1 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      {product.brand}
                    </span>
                    <h3 className="text-xs sm:text-sm font-bold text-gray-900 leading-snug line-clamp-2 mt-0.5 group-hover:text-[#008239] transition-colors">
                      {product.name}
                    </h3>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {product.variant || `${product.unit_of_measurement}`}
                    </p>

                    {/* Pricing */}
                    <div className="mt-2.5 flex items-baseline gap-1.5">
                      <span className="text-base sm:text-lg font-black text-[#004724]">
                        AED {product.price_aed.toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-400 line-through">AED {mrp}</span>
                    </div>
                  </div>

                  {/* Add to Basket Action */}
                  <div className="mt-3 pt-2 border-t border-gray-100">
                    <button
                      type="button"
                      onClick={() => handleDirectAddToCart(product, 1)}
                      disabled={!product.is_available || product.stock_quantity <= 0 || isAdding}
                      className={`w-full py-2 px-3 rounded-xl text-xs font-black flex items-center justify-center gap-1.5 transition-all shadow-xs ${
                        isAdding
                          ? "bg-[#004724] text-white"
                          : product.is_available && product.stock_quantity > 0
                          ? "bg-[#00e575] hover:bg-[#00b853] text-[#09281a] shadow-emerald-500/20"
                          : "bg-gray-100 text-gray-400 cursor-not-allowed"
                      }`}
                    >
                      {isAdding ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Added to Basket</span>
                        </>
                      ) : (
                        <>
                          <Plus className="w-3.5 h-3.5" />
                          <span>Add to Basket</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>

      {/* 5. Sticky Floating Action Button (FAB) -> Pops Up Assistant */}
      <button
        type="button"
        onClick={() => setIsAssistantOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 py-3.5 px-5 rounded-full bg-[#004724] hover:bg-[#00381c] text-white font-extrabold text-sm shadow-2xl shadow-emerald-950/40 border-2 border-[#00e575] transition-transform hover:scale-105"
      >
        <div className="w-7 h-7 rounded-full bg-[#00e575] flex items-center justify-center text-[#09281a]">
          <Bot className="w-4 h-4 fill-current" />
        </div>
        <span>Ask Careem AI</span>
        <span className="w-2.5 h-2.5 rounded-full bg-[#00e575] animate-ping" />
      </button>

      {/* 6. Careem AI Shopping Assistant Pop-Up Modal */}
      {isAssistantOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-3xl max-w-xl w-full h-[90vh] max-h-[720px] shadow-2xl border border-gray-200 flex flex-col overflow-hidden relative animate-slide-up">
            {/* Pop-up Top Bar */}
            <div className="p-4 bg-[#004724] text-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-[#00e575] text-[#09281a] flex items-center justify-center font-black">
                  <Bot className="w-5 h-5 fill-current" />
                </div>
                <div>
                  <h3 className="text-sm font-black tracking-tight">KON Shopping Assistant</h3>
                  <p className="text-[10px] text-emerald-200">Governed Conversational AI Shopping</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* TTS Audio Readback Toggle */}
                <button
                  type="button"
                  onClick={toggleTTS}
                  title={ttsEnabled ? "Mute Voice Readback" : "Enable Voice Readback"}
                  className={`px-2 py-1 rounded-lg text-xs flex items-center gap-1.5 transition-colors ${
                    ttsEnabled
                      ? "bg-[#00e575] text-[#09281a] font-bold shadow-xs"
                      : "bg-[#006031] text-emerald-200 hover:text-white"
                  }`}
                >
                  {ttsEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                  <span className="text-[10px] hidden sm:inline">
                    {ttsEnabled ? "Voice On" : "Muted"}
                  </span>
                </button>

                {/* Close Pop-Up Button */}
                <button
                  type="button"
                  onClick={() => setIsAssistantOpen(false)}
                  className="p-1.5 rounded-lg bg-[#006031] hover:bg-[#008239] text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Digital Human Avatar Banner */}
            <div className="p-3 bg-emerald-50/60 border-b border-gray-200 shrink-0">
              <AvatarPlaceholder
                isSpeaking={isSpeaking}
                isListening={isListening}
                isThinking={isLoading}
                avatarName="KON Voice AI"
                avatarRole="Conversational AI Governance Bridge"
              />
            </div>

            {/* Conversation Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-[#f8fafc]">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onSelectProduct={async (pid, qty) => {
                    setIsAddingProduct(true);
                    try {
                      const chatRes = await confirmAssistantSelection(pid, qty, sessionId);
                      if (chatRes.cart) {
                        setCart(chatRes.cart);
                      }
                      setMessages((prev) => [
                        ...prev,
                        {
                          id: "conf-" + Date.now(),
                          role: "assistant",
                          content: chatRes.message || `Added selected option to your basket.`,
                          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                          action_taken: "add_to_cart",
                        },
                      ]);
                    } catch (err: any) {
                      alert(err.response?.data?.detail || "Failed to add product to basket.");
                    } finally {
                      setIsAddingProduct(false);
                    }
                  }}
                  isAddingProduct={isAddingProduct}
                />
              ))}

              {isLoading && (
                <div className="flex items-center gap-2 p-3 bg-white rounded-2xl max-w-xs text-xs text-gray-500 border border-gray-200 shadow-xs animate-fade-in">
                  <span className="w-2 h-2 rounded-full bg-[#00e575] animate-ping" />
                  <span>Processing...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Voice / Tap Suggestion Chips */}
            <div className="px-3 py-2 bg-white border-t border-gray-200 overflow-x-auto flex gap-1.5 scrollbar-none">
              {quickPrompts.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSendMessage(p)}
                  disabled={isLoading}
                  className="whitespace-nowrap px-3 py-1 rounded-full bg-emerald-50 hover:bg-emerald-100 text-[#004724] text-[11px] font-bold border border-emerald-200 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Input Controls (Voice & Text) */}
            <div className="p-3 bg-white border-t border-gray-200">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Speak into mic or type (e.g. '2 kg atta and chicken')..."
                  disabled={isLoading}
                  className="flex-1 bg-gray-50 border border-gray-300 rounded-full px-4 py-2.5 text-xs sm:text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-[#00e575] focus:ring-2 focus:ring-[#00e575]/20 transition-all"
                />

                {/* Voice Microphone Input */}
                <VoiceInput
                  disabled={isLoading}
                  onTranscript={(transcript) => handleSendMessage(transcript)}
                  onListeningChange={setIsListening}
                />

                {/* Send Button */}
                <button
                  type="submit"
                  disabled={!inputText.trim() || isLoading}
                  className="p-2.5 sm:p-3 rounded-full bg-[#00e575] hover:bg-[#00b853] disabled:opacity-40 text-[#09281a] font-black transition-all shadow-md shadow-emerald-500/20"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* 7. Careem Quik Cart Drawer */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-white shadow-2xl border-l border-gray-200 transform transition-transform duration-300 ${
          isCartOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <BasketPanel
          cart={cart}
          sessionId={sessionId}
          onCartChange={(updated) => setCart(updated)}
          isLoading={isLoading}
          onClose={() => setIsCartOpen(false)}
        />
      </div>

      {/* Backdrop overlay for Cart drawer */}
      {isCartOpen && (
        <div
          onClick={() => setIsCartOpen(false)}
          className="fixed inset-0 bg-black/50 backdrop-blur-xs z-40 transition-opacity"
        />
      )}

      {/* 8. KON Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12 py-8 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto px-4 space-y-1.5">
          <p className="font-extrabold text-[#004724] text-sm">
            KON Commerce Demo • Governed Conversational AI Shopping
          </p>
          <p className="text-[11px] text-gray-400">
            Mock grocery catalogue demonstrating how an enterprise conversational agent could interact with a retailer's commerce APIs through a governed tool layer.
          </p>
        </div>
      </footer>
    </div>
  );
}
