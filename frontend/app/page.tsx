// frontend/app/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { User } from "@/lib/types";

const DEMO_ACCOUNTS = [
  { username: "dr.mehta",     password: "doctor",            role: "doctor" },
  { username: "nurse.priya",  password: "nurse",             role: "nurse" },
  { username: "billing.ravi", password: "billing_executive", role: "billing_executive" },
  { username: "tech.anand",   password: "technician",        role: "technician" },
  { username: "admin.sys",    password: "admin",             role: "admin" },
];

const ROLE_COLORS: Record<string, string> = {
  doctor:            "bg-blue-100 text-blue-800",
  nurse:             "bg-green-100 text-green-800",
  billing_executive: "bg-yellow-100 text-yellow-800",
  technician:        "bg-purple-100 text-purple-800",
  admin:             "bg-red-100 text-red-800",
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const handleLogin = async (u?: string, p?: string) => {
    const user = u || username;
    const pass = p || password;
    setLoading(true);
    setError("");
    try {
      const data = await login(user, pass);
      localStorage.setItem("medibot_user", JSON.stringify(data));
      router.push("/chat");
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🏥</div>
          <h1 className="text-2xl font-bold text-gray-900">MediBot</h1>
          <p className="text-gray-500 text-sm mt-1">
            MediAssist Health Network · Internal Assistant
          </p>
        </div>

        {/* Login form */}
        <div className="space-y-4 mb-6">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            onClick={() => handleLogin()}
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </div>

        {/* Demo accounts */}
        <div>
          <p className="text-xs text-gray-400 text-center mb-3">
            Demo accounts — click to login instantly
          </p>
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                onClick={() => handleLogin(acc.username, acc.password)}
                className="w-full flex items-center justify-between px-4 py-2 rounded-lg border border-gray-100 hover:bg-gray-50 transition text-sm"
              >
                <span className="text-gray-700 font-medium">{acc.username}</span>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${ROLE_COLORS[acc.role]}`}>
                  {acc.role}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}