import { NextResponse } from "next/server";
import { backendBaseUrl, TOKEN_COOKIE } from "@/lib/backend-proxy";

export async function POST(request: Request) {
  const payload = await request.text();
  const response = await fetch(`${backendBaseUrl()}/api/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: payload,
    cache: "no-store"
  });
  const data = await response.json();
  if (!response.ok || !data.access_token) {
    return NextResponse.json(
      { detail: data.detail || "Invalid email or password" },
      { status: response.status }
    );
  }

  const result = NextResponse.json({ role: data.role, name: data.name });
  result.cookies.set(TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8
  });
  return result;
}
