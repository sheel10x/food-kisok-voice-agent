"use client";

import { useState, useEffect } from 'react';
import { MENU_CATEGORIES, MENU_ITEMS, CATEGORY_META } from '@/data/menuData';
import { useMoshi } from '@/hooks/useMoshi';

// Soft two-stop gradient per category — used on item photo tiles so each
// section reads at a glance, before you even look at the label.
const CATEGORY_TINT = {
  "Burgers":         ["#ffeedd", "#fbe0ad"],
  "Breakfast":       ["#fff3d6", "#ffe3b0"],
  "Snacks & Sides":  ["#ffe7d2", "#ffd2a8"],
  "Happy Meal":      ["#ffe0ec", "#ffc9de"],
  "Desserts":        ["#f3e3ff", "#e4c6fa"],
  "Beverages":       ["#dceefb", "#bfe0f5"],
  "McCafé":          ["#e9dfd3", "#d8c7b0"],
};

function tintStyle(category) {
  const [a, b] = CATEGORY_TINT[category] || ["#ffeedd", "#fbe0ad"];
  return { backgroundImage: `linear-gradient(145deg, ${a}, ${b})` };
}

// The signature element: a voice orb whose rings read the AI's state.
function VoiceOrb({ state, isConnected }) {
  const isSpeaking = state === 'SPEAKING';
  const isListening = state === 'LISTENING';
  const isProcessing = state === 'PROCESSING';

  const glyph = isListening ? '🎙️' : isSpeaking ? '🗣️' : isProcessing ? '···' : '🤖';

  return (
    <div className="relative w-16 h-16 shrink-0">
      {isConnected && (
        <>
          <span
            className={`absolute inset-0 rounded-full ${isListening ? 'animate-ping' : ''}`}
            style={{ backgroundColor: 'color-mix(in srgb, var(--color-chili) 35%, transparent)' }}
          />
          <span
            className={`absolute -inset-1.5 rounded-full border-2 ${isSpeaking ? 'animate-pulse' : ''}`}
            style={{ borderColor: 'var(--color-gold)' }}
          />
        </>
      )}
      <div
        className="relative w-16 h-16 rounded-full flex items-center justify-center text-2xl shadow-md"
        style={{
          backgroundImage: isConnected
            ? 'linear-gradient(145deg, var(--color-chili), var(--color-gold))'
            : 'linear-gradient(145deg, #e7dccb, #d8c7b0)',
        }}
      >
        <span className={isProcessing ? 'animate-pulse' : ''}>{glyph}</span>
      </div>
    </div>
  );
}

export default function Home() {
  const {
    isConnected,
    state,
    message,
    cart,
    transcript,
    monologue,
    activeCategory: voiceCategory,
    connect,
    disconnect,
    sendAction
  } = useMoshi();

  const [activeCategory, setActiveCategory] = useState(MENU_CATEGORIES[0]);

  // Voice command ("show me beverages") drives the same state as tapping —
  // the UI always reflects whichever one happened last.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing from the websocket (external system), not derived from render state
    if (voiceCategory) setActiveCategory(voiceCategory);
  }, [voiceCategory]);

  // Auto-connect when the page opens
  useEffect(() => {
    connect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleItemClick = (item) => {
    sendAction('add', { item: item.name });
  };

  const handleRemoveClick = (cartId) => {
    sendAction('remove', { cart_id: cartId });
  };

  const isSpeaking = state === 'SPEAKING';
  const isListening = state === 'LISTENING';
  const isProcessing = state === 'PROCESSING';

  const categoryItems = MENU_ITEMS.filter(i => i.category === activeCategory);

  return (
    <div className="min-h-screen flex flex-col font-sans" style={{ background: 'var(--color-cream)', color: 'var(--color-ink)' }}>
      {/* HEADER */}
      <header
        className="px-6 py-4 flex justify-between items-center sticky top-0 z-50 border-b"
        style={{ background: 'var(--color-paper)', borderColor: 'var(--color-line)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center text-xl shadow-sm"
            style={{ backgroundImage: 'linear-gradient(145deg, var(--color-chili), var(--color-gold))' }}
          >
            🍔
          </div>
          <div>
            <h1 className="text-2xl font-extrabold leading-none" style={{ fontFamily: 'var(--font-display)' }}>
              Hedes Kiosk
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-ink-soft)' }}>Tap to order, or just talk</p>
          </div>
        </div>
        <button
          onClick={isConnected ? disconnect : connect}
          className="px-6 py-2.5 rounded-full font-semibold transition-all flex items-center gap-2 shadow-sm"
          style={
            isConnected
              ? { background: '#fdeceb', color: 'var(--color-chili-dark)', border: '1px solid #f4c7bf' }
              : { backgroundImage: 'linear-gradient(145deg, var(--color-chili), var(--color-chili-dark))', color: '#fff' }
          }
        >
          {isConnected ? (
            <>
              <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--color-chili)' }}></span>
              End voice order
            </>
          ) : (
            <>
              <span className="text-lg">🎙️</span>
              Order by voice
            </>
          )}
        </button>
      </header>

      <main className="flex-1 flex overflow-hidden">
        {/* LEFT RAIL: Categories */}
        <nav
          className="w-60 shrink-0 border-r overflow-y-auto custom-scrollbar py-4 px-3 hidden sm:block"
          style={{ background: 'var(--color-paper)', borderColor: 'var(--color-line)' }}
        >
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-wide" style={{ color: 'var(--color-ink-soft)' }}>
            Discover our menu
          </p>
          <ul className="space-y-1">
            {MENU_CATEGORIES.map(cat => {
              const meta = CATEGORY_META[cat] || {};
              const active = activeCategory === cat;
              return (
                <li key={cat}>
                  <button
                    onClick={() => setActiveCategory(cat)}
                    className="w-full flex items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition-all"
                    style={
                      active
                        ? { backgroundImage: 'linear-gradient(145deg, var(--color-chili), var(--color-chili-dark))', color: '#fff' }
                        : { color: 'var(--color-ink)' }
                    }
                    onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'var(--color-peach)'; }}
                    onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span
                      className="w-9 h-9 rounded-xl flex items-center justify-center text-lg shrink-0"
                      style={active ? { background: 'rgba(255,255,255,0.2)' } : { background: 'var(--color-cream)' }}
                    >
                      {meta.icon || '🍽️'}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold text-sm truncate">{cat}</span>
                      <span
                        className="block text-xs truncate"
                        style={{ color: active ? 'rgba(255,255,255,0.85)' : 'var(--color-ink-soft)' }}
                      >
                        {meta.blurb}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* CENTER: Item Grid */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 custom-scrollbar">
          {/* Mobile category strip (shown when the sidebar is hidden) */}
          <div className="flex gap-2 overflow-x-auto pb-4 sm:hidden custom-scrollbar">
            {MENU_CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className="px-4 py-2 rounded-full whitespace-nowrap text-sm font-semibold"
                style={
                  activeCategory === cat
                    ? { background: 'var(--color-chili)', color: '#fff' }
                    : { background: 'var(--color-peach)', color: 'var(--color-ink)' }
                }
              >
                {(CATEGORY_META[cat]?.icon || '')} {cat}
              </button>
            ))}
          </div>

          <div className="flex items-baseline justify-between mb-6">
            <h2 className="text-3xl font-extrabold" style={{ fontFamily: 'var(--font-display)' }}>
              {activeCategory}
            </h2>
            <span className="text-sm" style={{ color: 'var(--color-ink-soft)' }}>
              {categoryItems.length} item{categoryItems.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {categoryItems.map(item => (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                className="group text-left rounded-3xl overflow-hidden shadow-sm hover:shadow-lg transition-all border"
                style={{ background: 'var(--color-paper)', borderColor: 'var(--color-line)' }}
              >
                <div className="h-28 flex items-center justify-center text-5xl transition-transform group-hover:scale-110" style={tintStyle(item.category)}>
                  {item.image}
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-sm leading-snug mb-2 line-clamp-2 min-h-[2.5rem]">{item.name}</h3>
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-extrabold" style={{ color: 'var(--color-chili)' }}>₹{item.price}</span>
                    <span
                      className="w-8 h-8 rounded-full flex items-center justify-center text-lg font-bold transition-colors"
                      style={{ background: 'var(--color-peach)', color: 'var(--color-chili-dark)' }}
                    >
                      +
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* RIGHT: Voice AI + Cart */}
        <div className="w-96 shrink-0 border-l flex flex-col hidden lg:flex" style={{ background: 'var(--color-paper)', borderColor: 'var(--color-line)' }}>

          {/* AI Voice Status Panel */}
          {isConnected && (
            <div className="p-5 border-b" style={{ borderColor: 'var(--color-line)', background: 'var(--color-cream)' }}>
              <div className="flex items-center gap-4 mb-3">
                <VoiceOrb state={state} isConnected={isConnected} />
                <div className="min-w-0">
                  <h3 className="font-bold text-base">{isListening ? 'Listening' : isSpeaking ? 'Speaking' : isProcessing ? 'Thinking' : state}</h3>
                  <p className="text-xs truncate" style={{ color: 'var(--color-ink-soft)' }}>{message}</p>
                </div>
              </div>

              {monologue && (
                <div
                  className="rounded-xl p-3 text-xs font-mono mb-3 border"
                  style={{ background: '#fff', borderColor: 'var(--color-line)', color: 'var(--color-ink-soft)' }}
                >
                  <span className="opacity-50">&gt; </span>{monologue}
                  {isSpeaking && <span className="animate-pulse">_</span>}
                </div>
              )}

              <div className="h-36 overflow-y-auto custom-scrollbar flex flex-col gap-2">
                {transcript.map((msg, i) => (
                  <div key={i} className={`flex ${msg.speaker === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className="max-w-[85%] rounded-2xl px-3 py-2 text-sm"
                      style={
                        msg.speaker === 'user'
                          ? { background: 'var(--color-gold-soft)', color: '#5a4109', borderBottomRightRadius: '0.25rem' }
                          : { background: 'var(--color-peach)', color: 'var(--color-chili-dark)', borderBottomLeftRadius: '0.25rem' }
                      }
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[11px] mt-3 text-center" style={{ color: 'var(--color-ink-soft)' }}>
                Try: <span className="italic">&quot;show me beverages&quot;</span> or <span className="italic">&quot;add a McAloo Tikki&quot;</span>
              </p>
            </div>
          )}

          {/* Cart Header */}
          <div className="p-5 pb-2 border-b" style={{ borderColor: 'var(--color-line)' }}>
            <h2 className="text-lg font-extrabold flex justify-between items-center" style={{ fontFamily: 'var(--font-display)' }}>
              Your Order
              <span className="text-xs font-semibold px-3 py-1 rounded-full" style={{ background: 'var(--color-peach)', color: 'var(--color-chili-dark)' }}>
                {cart.items?.length || 0} item{(cart.items?.length || 0) !== 1 ? 's' : ''}
              </span>
            </h2>
          </div>

          {/* Cart Items */}
          <div className="flex-1 overflow-y-auto p-5 space-y-3 custom-scrollbar">
            {(!cart.items || cart.items.length === 0) ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-3" style={{ color: 'var(--color-ink-soft)' }}>
                <div className="text-6xl">🛒</div>
                <p className="font-medium">Your cart is empty</p>
                {!isConnected && (
                  <p className="text-sm">Tap a menu item to add it,<br/>or start a voice order.</p>
                )}
              </div>
            ) : (
              cart.items.map((item) => (
                <div key={item.cart_id} className="flex items-center gap-3 rounded-2xl p-3 group" style={{ background: 'var(--color-cream)' }}>
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0" style={{ background: 'var(--color-peach)' }}>
                    {MENU_ITEMS.find(m => m.id === item.id)?.image || "🍔"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-sm truncate">{item.name}</h4>
                    <p className="text-xs" style={{ color: 'var(--color-ink-soft)' }}>₹{item.price} × {item.quantity}</p>
                  </div>
                  <div className="font-bold" style={{ color: 'var(--color-chili)' }}>
                    ₹{item.price * item.quantity}
                  </div>
                  <button
                    onClick={() => handleRemoveClick(item.cart_id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity w-7 h-7 rounded-lg flex items-center justify-center ml-1"
                    style={{ color: 'var(--color-chili-dark)' }}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Cart Footer */}
          <div className="p-5 border-t" style={{ borderColor: 'var(--color-line)', background: 'var(--color-cream)' }}>
            <div className="flex justify-between items-center mb-4">
              <span style={{ color: 'var(--color-ink-soft)' }}>Total</span>
              <span className="text-2xl font-extrabold">₹{cart.total || 0}</span>
            </div>
            <button
              className="w-full py-3.5 rounded-2xl font-bold text-base transition-all flex items-center justify-center gap-2 shadow-sm"
              style={{ backgroundImage: 'linear-gradient(145deg, var(--color-chili), var(--color-chili-dark))', color: '#fff' }}
            >
              Checkout <span>→</span>
            </button>
          </div>
        </div>
      </main>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--color-line);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--color-gold-soft);
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
