import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const backend = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);
const auth = new GoogleAuth();

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  const allowed =
    /^(health|auth\/(login|register|me|logout)|uploads|pqrs(\/[a-f0-9]{32}(\/(analyze|result|file))?)?)$/;
  if (!allowed.test(path))
    return NextResponse.json(
      { detail: "Ruta no encontrada." },
      { status: 404 },
    );
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    const host =
      request.headers.get("x-forwarded-host") || request.headers.get("host");
    if (origin && new URL(origin).host !== host)
      return NextResponse.json(
        { detail: "Origen no permitido." },
        { status: 403 },
      );
  }
  if (path === "auth/logout") {
    const response = NextResponse.json({ ok: true });
    response.cookies.delete("pqr_session");
    return response;
  }
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const token = request.cookies.get("pqr_session")?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    if (process.env.BACKEND_IAM_AUTH === "true") {
      const client = await auth.getIdTokenClient(backend);
      const serviceHeaders = await client.getRequestHeaders();
      headers.set(
        "X-Serverless-Authorization",
        serviceHeaders.get("authorization") || "",
      );
    }
    const maxBytes = (Number(process.env.MAX_UPLOAD_MB || 5) + 1) * 1024 * 1024;
    let body: Uint8Array | undefined;
    if (request.method === "POST" && request.body) {
      const reader = request.body.getReader();
      const chunks: Uint8Array[] = [];
      let length = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.length;
        if (length > maxBytes) {
          await reader.cancel();
          return NextResponse.json(
            { detail: "El archivo supera el límite de 5 MB." },
            { status: 413 },
          );
        }
        chunks.push(value);
      }
      body = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.length;
      }
    }
    const upstream = await fetch(`${backend}/${path}`, {
      method: request.method,
      headers,
      body: body as BodyInit | undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(105000),
    });
    if ((path === "auth/login" || path === "auth/register") && upstream.ok) {
      const data = await upstream.json();
      const response = NextResponse.json({ email: data.email });
      response.cookies.set("pqr_session", data.token, {
        httpOnly: true,
        sameSite: "strict",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: data.expires_in,
      });
      return response;
    }
    const response = new NextResponse(upstream.body, {
      status: upstream.status,
    });
    for (const name of ["content-type", "content-disposition"]) {
      const value = upstream.headers.get(name);
      if (value) response.headers.set(name, value);
    }
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return NextResponse.json(
      {
        detail:
          "No se pudo conectar con el servidor. Comprueba que el backend esté iniciado e intenta nuevamente.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
