import { NextResponse } from "next/server";

export function proxy() {
  // Since we use localStorage for auth (client-side only),
  // we can't reliably check auth state in server-side proxy.
  // Authentication is handled by client-side ProtectedRoute component.
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
