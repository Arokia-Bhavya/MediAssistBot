// frontend/app/chat/page.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { chat } from "@/lib/api";
import { User, Message } from "@/lib/types";

const ROLE_COLORS: Record<string, string> = {
  doctor:            "bg-blue-100 text-blue-800",
  nurse:             "bg-green-100 text-green-800",
  billing_executive: "bg-yellow-100 text-yellow-800",
  technician:        "bg-purple-100 text-purple-800",
  admin:             "bg-red-100 text-red-800",
};

const COLLECTION_COLORS: Record<string, string> = {
  general:   "bg-gray-100 text-gray-700",
  clinical:  "bg-blue-100 text-blue-700",
  nursing:   "bg-green-100 text-green-700",
  billing:   "bg-yellow-100 text-yellow-700",
  equipment: "bg-purple-100 text-purple-700",
  database:  "bg-orange-100 text-orange-700",
};

export default function ChatPage() {
  const router  = useRouter();
  const bottomRef = useRef<HTMLDivElement>(null);

  const [user, setUser]         = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);

  // Load user from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("medibot_user");
    if (!stored) { router.push("/"); return; }
    const u: User = JSON.parse(stored);
    setUser(u);

    // Welcome message
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: `Hello! I'm MediBot. You're logged in as **${u.username}** with role **${u.role}**. You have access to the **${u.accessible_collections.join(", ")}** collections. How can I help you today?`,
      timestamp: new Date(),
    }]);
  }, [router]);

  // Auto scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || !user || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await chat(userMsg.content, user.token);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        retrieval_type: res.retrieval_type,
        sql: res.sql,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    if (typeof window === "undefined") return;

    window.localStorage.removeItem("medibot_user");
    router.replace("/");
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏥</span>
          <div>
            <h1 className="font-bold text-gray-900">MediBot</h1>
            <p className="text-xs text-gray-500">MediAssist Health Network</p>
          </div>
        </div>

        {/* Role badge + collections */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex gap-1">
            {user.accessible_collections.map((col) => (
              <span key={col} className={`text-xs px-2 py-1 rounded-full ${COLLECTION_COLORS[col]}`}>
                {col}
              </span>
            ))}
          </div>
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${ROLE_COLORS[user.role]}`}>
            {user.role}
          </span>
          <button
            onClick={handleLogout}
            className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 max-w-4xl mx-auto w-full">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-2xl ${msg.role === "user" ? "order-2" : "order-1"}`}>

              {/* Message bubble */}
              <div className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
              }`}>
                {msg.content}
              </div>

              {/* Retrieval type badge */}
              {msg.retrieval_type && (
                <div className="mt-2 flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    msg.retrieval_type === "sql_rag"
                      ? "bg-orange-100 text-orange-700"
                      : "bg-indigo-100 text-indigo-700"
                  }`}>
                    {msg.retrieval_type === "sql_rag" ? "⚡ SQL RAG" : "🔍 Hybrid RAG"}
                  </span>
                </div>
              )}

              {/* SQL query (for sql_rag responses) */}
              {msg.sql && (
                <div className="mt-2 bg-gray-900 rounded-lg px-4 py-3">
                  <p className="text-xs text-gray-400 mb-1">Generated SQL</p>
                  <code className="text-xs text-green-400 whitespace-pre-wrap">{msg.sql}</code>
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-400">Sources</p>
                  {msg.sources.map((src, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs bg-white border border-gray-100 rounded-lg px-3 py-2">
                      <span className="text-gray-400">📄</span>
                      <span className="font-medium text-gray-700">{src.source_document}</span>
                      <span className="text-gray-400">·</span>
                      <span className="text-gray-500">{src.section_title}</span>
                      <span className={`ml-auto px-2 py-0.5 rounded-full ${COLLECTION_COLORS[src.collection] || "bg-gray-100 text-gray-600"}`}>
                        {src.collection}
                      </span>
                    </div>
                  ))}
                </div>
              )}

            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask MediBot anything..."
            disabled={loading}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white rounded-xl px-6 py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          Logged in as <strong>{user.username}</strong> · {user.role} · Access: {user.accessible_collections.join(", ")}
        </p>
      </div>
    </div>
  );
}