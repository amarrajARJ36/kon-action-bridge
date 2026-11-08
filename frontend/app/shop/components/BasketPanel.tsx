"use client";

import React, { useState } from "react";
import {
  ShoppingBag,
  Trash2,
  Plus,
  Minus,
  ArrowRight,
  Wheat,
  Drumstick,
  Apple,
  Egg,
  Milk,
  Droplet,
  Package,
  Zap,
  CheckCircle2,
  X,
} from "lucide-react";
import { CartResponse } from "@/lib/types";
import { clearCart, getCheckoutPreview, removeCartItem, updateCartItem } from "@/lib/api";

interface BasketPanelProps {
  cart: CartResponse | null;
  sessionId: string;
  onCartChange: (updatedCart: CartResponse) => void;
  isLoading?: boolean;
  onClose?: () => void;
}

export function BasketPanel({ cart, sessionId, onCartChange, isLoading = false, onClose }: BasketPanelProps) {
  const [isUpdating, setIsUpdating] = useState<string | null>(null);
  const [checkoutModalOpen, setCheckoutModalOpen] = useState(false);
  const [checkoutData, setCheckoutData] = useState<CartResponse | null>(null);

  const getProductCategoryIcon = (category: string = "") => {
    const c = category.toLowerCase();
    if (c.includes("atta") || c.includes("flour")) return Wheat;
    if (c.includes("chicken")) return Drumstick;
    if (c.includes("banana")) return Apple;
    if (c.includes("egg")) return Egg;
    if (c.includes("milk")) return Milk;
    if (c.includes("oil")) return Droplet;
    return Package;
  };

  const handleQuantityDelta = async (cartItemId: string, currentQty: number, delta: number) => {
    const newQty = currentQty + delta;
    if (newQty <= 0) {
      handleRemoveItem(cartItemId);
      return;
    }

    try {
      setIsUpdating(cartItemId);
      const updated = await updateCartItem(cartItemId, newQty, sessionId);
      onCartChange(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to update quantity");
    } finally {
      setIsUpdating(null);
    }
  };

  const handleRemoveItem = async (cartItemId: string) => {
    try {
      setIsUpdating(cartItemId);
      const updated = await removeCartItem(cartItemId, sessionId);
      onCartChange(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to remove item");
    } finally {
      setIsUpdating(null);
    }
  };

  const handleClearCart = async () => {
    if (!confirm("Are you sure you want to empty your basket?")) return;
    try {
      await clearCart(sessionId);
      onCartChange({
        id: cart?.id || "",
        user_id: cart?.user_id || "",
        session_id: sessionId,
        items: [],
        subtotal_aed: 0.0,
        vat_aed: 0.0,
        grand_total_aed: 0.0,
        item_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to clear basket");
    }
  };

  const handleTriggerCheckout = async () => {
    try {
      const preview = await getCheckoutPreview(sessionId);
      setCheckoutData(preview);
      setCheckoutModalOpen(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to generate checkout preview");
    }
  };

  const items = cart?.items || [];
  const subtotal = cart?.subtotal_aed || 0.0;
  const vat = cart?.vat_aed || 0.0;
  const grandTotal = cart?.grand_total_aed || 0.0;

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* KON Commerce Cart Header */}
      <div className="p-4 bg-[#004724] text-white flex items-center justify-between shrink-0 shadow-xs">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#00e575] text-[#09281a] flex items-center justify-center font-black">
            <ShoppingBag className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-extrabold tracking-tight">KON Commerce Basket</h3>
              <span className="px-1.5 py-0.2 rounded bg-[#00e575] text-[#09281a] text-[9px] font-black uppercase">
                Demo
              </span>
            </div>
            <span className="text-[11px] text-emerald-200">
              {cart?.item_count || 0} {cart?.item_count === 1 ? "item" : "items"} • Governed Sandbox
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {items.length > 0 && (
            <button
              type="button"
              onClick={handleClearCart}
              className="text-xs text-emerald-200 hover:text-white underline font-semibold transition-colors"
            >
              Empty
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg bg-[#008239] hover:bg-[#00b853] text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Cart Items List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#f8fafc]">
        {items.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-400">
            <div className="w-16 h-16 rounded-full bg-emerald-50 text-[#00b853] flex items-center justify-center mb-3 border border-emerald-100">
              <ShoppingBag className="w-8 h-8 stroke-1" />
            </div>
            <h4 className="text-sm font-bold text-gray-800">Your basket is empty</h4>
            <p className="text-xs text-gray-500 mt-1 max-w-[210px]">
              Add items from the catalogue or tap the AI Assistant to voice-order groceries!
            </p>
          </div>
        ) : (
          items.map((item) => {
            const Icon = getProductCategoryIcon(item.product?.category);
            const isLineUpdating = isUpdating === item.id;

            return (
              <div
                key={item.id}
                className="p-3 rounded-xl border border-gray-200 bg-white hover:border-[#00e575] transition-all shadow-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5">
                    <div className="w-10 h-10 rounded-lg bg-emerald-50 text-[#008239] flex items-center justify-center shrink-0 border border-emerald-100">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-gray-900 leading-snug">
                        {item.product?.name || "Grocery Item"}
                      </h4>
                      <p className="text-[11px] text-gray-500">
                        {item.product?.brand} • AED {item.unit_price_aed.toFixed(2)}/{item.product?.unit_of_measurement || "kg"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRemoveItem(item.id)}
                    disabled={isLineUpdating}
                    className="text-gray-400 hover:text-rose-600 transition-colors p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Subtotal & Stepper */}
                <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between">
                  <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
                    <button
                      type="button"
                      onClick={() => handleQuantityDelta(item.id, item.quantity, -1)}
                      disabled={isLineUpdating}
                      className="px-2 py-1 text-gray-700 hover:bg-emerald-100 transition-colors text-xs font-bold"
                    >
                      <Minus className="w-3 h-3" />
                    </button>
                    <span className="px-2 text-xs font-bold text-gray-900">
                      {item.quantity} {item.product?.unit_of_measurement || "kg"}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleQuantityDelta(item.id, item.quantity, 1)}
                      disabled={isLineUpdating}
                      className="px-2 py-1 text-gray-700 hover:bg-emerald-100 transition-colors text-xs font-bold"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>

                  <span className="text-xs font-black text-[#004724]">
                    AED {item.subtotal_aed.toFixed(2)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Price Breakdown & Careem Pay Action */}
      {items.length > 0 && (
        <div className="p-4 border-t border-gray-200 bg-white shrink-0 shadow-lg">
          <div className="space-y-1.5 text-xs text-gray-600 mb-3">
            <div className="flex justify-between">
              <span>Items Subtotal ({items.length})</span>
              <span className="font-semibold text-gray-900">AED {subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>UAE VAT (5%)</span>
              <span className="font-semibold text-gray-900">AED {vat.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-[#008239]">
              <span className="flex items-center gap-1 font-semibold">
                <Zap className="w-3 h-3 fill-current" /> Quik Delivery (15 mins)
              </span>
              <span className="font-extrabold uppercase tracking-wide">FREE</span>
            </div>
            <div className="pt-2 border-t border-gray-100 flex justify-between text-sm font-black text-gray-900">
              <span>Total Payable</span>
              <span className="text-base text-[#004724]">AED {grandTotal.toFixed(2)}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleTriggerCheckout}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-[#00e575] hover:bg-[#00b853] text-[#09281a] font-black text-sm shadow-md shadow-emerald-500/25 transition-all uppercase tracking-wide"
          >
            <span>Generate Order Preview</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Non-Binding Checkout Preview Modal */}
      {checkoutModalOpen && checkoutData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100">
            <div className="flex items-center gap-2.5 text-[#008239] mb-4">
              <CheckCircle2 className="w-6 h-6 text-[#00e575]" />
              <h3 className="text-base font-extrabold text-gray-900">Non-Binding Order Preview</h3>
            </div>

            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-[#004724] mb-4">
              <span className="font-bold">Governance Mock Disclosure:</span> {checkoutData.note || "Governed prototype. Non-binding preview only; no actual payment charged or order dispatched."}
            </div>

            <div className="space-y-2 text-xs mb-4 max-h-48 overflow-y-auto divide-y divide-gray-100">
              {checkoutData.items.map((it) => (
                <div key={it.id} className="pt-2 flex justify-between text-gray-700">
                  <span>
                    {it.quantity}x {it.product?.name}
                  </span>
                  <span className="font-bold">AED {it.subtotal_aed.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-gray-200 space-y-1 mb-6">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Items Subtotal</span>
                <span>AED {checkoutData.subtotal_aed.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-xs text-gray-600">
                <span>UAE VAT (5%)</span>
                <span>AED {checkoutData.vat_aed.toFixed(2)}</span>
              </div>
              <div className="pt-1.5 border-t border-gray-100 flex justify-between font-black text-sm text-gray-900">
                <span>Total Amount</span>
                <span className="text-[#004724]">AED {checkoutData.grand_total_aed.toFixed(2)}</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setCheckoutModalOpen(false)}
              className="w-full py-3 rounded-xl bg-[#00e575] hover:bg-[#00b853] text-[#09281a] font-extrabold text-xs transition-colors"
            >
              Close & Return to Store
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
