import { Inter } from "next/font/google";
import "./globals.css";
import ConnectivityBadge from "../components/ConnectivityBadge";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Rural MediBot — Offline-First Health Assistant",
  description: "Offline-first AI healthcare assistant for rural communities.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "MediBot",
  },
};

export const viewport = {
  themeColor: "#020617",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#020617" />
        <link rel="apple-touch-icon" href="/globe.svg" />
      </head>
      <body className={`${inter.className} bg-slate-950 text-white antialiased relative`}>
        <div id="sw-registration" dangerouslySetInnerHTML={{ __html: `
          <script>
            if ('serviceWorker' in navigator) {
              window.addEventListener('load', function() {
                navigator.serviceWorker.register('/sw.js').then(function(registration) {
                  console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }, function(err) {
                  console.log('ServiceWorker registration failed: ', err);
                });
              });
            }
          </script>
        `}} />
        <div className="fixed top-4 right-4 z-50">
          <ConnectivityBadge />
        </div>
        {children}
      </body>
    </html>
  );
}
