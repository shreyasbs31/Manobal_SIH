import { type NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "manobal.demo_gate";

function gateRequired(): boolean {
  const value = process.env.DEMO_GATE_REQUIRED?.trim().toLowerCase();
  return value === "1" || value === "true";
}

export function middleware(request: NextRequest) {
  if (!gateRequired() || request.nextUrl.pathname.startsWith("/access")) {
    return NextResponse.next();
  }
  if (request.cookies.has(COOKIE_NAME)) {
    return NextResponse.next();
  }
  const accessUrl = new URL("/access", request.url);
  accessUrl.searchParams.set(
    "next",
    `${request.nextUrl.pathname}${request.nextUrl.search}`,
  );
  return NextResponse.redirect(accessUrl);
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|sw.js|manifest.webmanifest|icons|audio).*)",
  ],
};
