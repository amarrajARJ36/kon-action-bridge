"use client";

import React, { useState } from "react";
import { Plus, Check, ShoppingBag, Wheat, Drumstick, Apple, Egg, Milk, Droplet } from "lucide-react";
import { Product } from "@/lib/types";

interface ProductCardProps {
  product: Product;
  onSelect: (productId: string, quantity: number) => void;
  isAdding?: boolean;
}

export function ProductCard({ product, onSelect, isAdding = false }: ProductCardProps) {
  const [selectedQty, setSelectedQty] = useState<number>(1);
  const [added, setAdded] = useState(false);

  const handleAdd = () => {
    onSelect(product.id, selectedQty);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const getCategoryIcon = (cat: string) => {
    const c = cat.toLowerCase();
    if (c.includes("atta") || c.includes("flour") || c.includes("grain")) return Wheat;
    if (c.includes("chicken") || c.includes("meat")) return Drumstick;
    if (c.includes("banana") || c.includes("fruit")) return Apple;
    if (c.includes("egg")) return Egg;
    if (c.includes("milk") || c.includes("dairy")) return Milk;
    if (c.includes("oil")) return Droplet;
    return ShoppingBag;
  };

  const Icon = getCategoryIcon(product.category);

  return (
    <div className="flex-shrink-0 w-60 bg-white border border-gray-200 hover:border-[#00e575] rounded-xl p-3 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="p-1.5 rounded-lg bg-emerald-50 text-[#008239]">
            <Icon className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
            {product.category}
          </span>
        </div>

        <h4 className="text-xs font-bold text-gray-900 leading-snug line-clamp-1">{product.name}</h4>
        <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">
          {product.brand} {product.variant ? `• ${product.variant}` : ""}
        </p>

        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-sm font-extrabold text-[#004724]">AED {product.price_aed.toFixed(2)}</span>
          <span className="text-[10px] text-gray-500">/ {product.unit_of_measurement}</span>
        </div>

        <div className="mt-1 text-[10px]">
          <span className={product.stock_quantity > 0 ? "text-emerald-700 font-bold" : "text-rose-600 font-medium"}>
            {product.stock_quantity > 0 ? `In Stock (${product.stock_quantity} ${product.unit_of_measurement})` : "Out of Stock"}
          </span>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-gray-100 flex items-center gap-2">
        <select
          value={selectedQty}
          onChange={(e) => setSelectedQty(Number(e.target.value))}
          disabled={!product.is_available || product.stock_quantity <= 0}
          className="bg-gray-50 border border-gray-300 rounded-lg text-xs py-1 px-1.5 text-gray-800 focus:outline-none focus:border-[#00e575]"
        >
          <option value={0.5}>0.5 {product.unit_of_measurement}</option>
          <option value={1}>1 {product.unit_of_measurement}</option>
          <option value={2}>2 {product.unit_of_measurement}</option>
          <option value={3}>3 {product.unit_of_measurement}</option>
          <option value={5}>5 {product.unit_of_measurement}</option>
        </select>

        <button
          type="button"
          onClick={handleAdd}
          disabled={!product.is_available || product.stock_quantity <= 0 || isAdding}
          className={`flex-1 flex items-center justify-center gap-1 py-1.5 px-2.5 rounded-lg text-xs font-bold transition-all ${
            added
              ? "bg-[#004724] text-white"
              : product.is_available && product.stock_quantity > 0
              ? "bg-[#00e575] hover:bg-[#00b853] text-[#09281a] shadow-xs font-black"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          }`}
        >
          {added ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>Added</span>
            </>
          ) : (
            <>
              <Plus className="w-3.5 h-3.5" />
              <span>Select & Add</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
