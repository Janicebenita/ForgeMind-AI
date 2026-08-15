import { NextResponse } from "next/server";
import { TOKEN_COOKIE } from "@/lib/backend-proxy";

export async function POST() {
  const result = NextResponse.json({ status: "signed_out" });
  result.cookies.set(TOKEN_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  return result;
}
