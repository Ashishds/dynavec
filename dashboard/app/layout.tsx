import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "dynavec · Observability",
  description: "Real-time retrieval observability for dynavec — latency, cache, traces.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        {/*
          Anti-flash theme script — runs synchronously before React hydration.
          Default is DARK (matches landing page). Applies html.dark unless user
          previously picked light mode.
        */}
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var s=localStorage.getItem('dynavec-theme');var dark=s==='light'?false:true;if(dark)document.documentElement.classList.add('dark');}catch(e){}})();` }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
