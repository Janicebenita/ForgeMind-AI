import { cookies } from "next/headers";

const TOKEN_COOKIE = "forgemind_token";

export function backendBaseUrl() {
  if (process.env.BACKEND_API_URL) return process.env.BACKEND_API_URL.replace(/\/$/, "");
  if (process.env.BACKEND_HOSTPORT) return `http://${process.env.BACKEND_HOSTPORT}`;
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  return "http://127.0.0.1:8000";
}

export async function proxyToBackend(request: Request, path: string) {
  const requestUrl = new URL(request.url);
  const destination = `${backendBaseUrl()}/api/${path}${requestUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("cookie");

  const token = (await cookies()).get(TOKEN_COOKIE)?.value;
  if (token) headers.set("authorization", `Bearer ${token}`);

  const body = request.method === "GET" || request.method === "HEAD"
    ? undefined
    : await request.arrayBuffer();
  const response = await fetch(destination, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
    redirect: "manual"
  });
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("set-cookie");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders
  });
}

export { TOKEN_COOKIE };
