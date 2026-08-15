"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/platform/brand-logo";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("plant.manager@forgemind.ai");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const response = await fetch("/api/session/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setError(payload.detail || "Sign-in failed.");
      setLoading(false);
      return;
    }
    router.replace("/platform/dashboard");
    router.refresh();
  }

  return (
    <main className="plant-os-bg grid min-h-screen place-items-center px-5 py-10">
      <form onSubmit={submit} className="glass w-full max-w-md rounded-3xl p-7 shadow-2xl">
        <div className="mb-7 flex items-center gap-4">
          <BrandLogo size="lg" />
          <div>
            <h1 className="text-2xl font-black">ForgeMind AI</h1>
            <p className="text-sm text-slate-400">Azure Conference Edition</p>
          </div>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Email
          <input className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none focus:border-cyan-300/60" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="mt-4 grid gap-2 text-sm font-semibold">
          Password
          <input className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3 text-white outline-none focus:border-cyan-300/60" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        {error ? <p className="mt-4 rounded-xl border border-rose-400/25 bg-rose-400/10 p-3 text-sm text-rose-100">{error}</p> : null}
        <button disabled={loading} className="mt-6 w-full rounded-xl bg-blue-500 px-4 py-3 font-bold text-white transition hover:bg-cyan-500 disabled:opacity-60">
          {loading ? "Signing in..." : "Enter Plant Intelligence"}
        </button>
        <p className="mt-4 text-xs leading-5 text-slate-500">Conference demonstration account. Operational decisions require authorized human review.</p>
      </form>
    </main>
  );
}
