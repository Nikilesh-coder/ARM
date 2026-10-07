import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "ARM — AI Academic Report Assistant",
  description: "Designed to follow your college format. AI-assisted academic project and seminar report generation from your authentic evidence.",
};

const themeScript = `
  (function() {
    try {
      var t = localStorage.getItem('arm_theme_preference');
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      var isDark = t === 'dark' || (!t && prefersDark) || (t === 'system' && prefersDark);
      if (isDark) {
        document.documentElement.classList.add('dark');
        document.documentElement.style.colorScheme = 'dark';
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.style.colorScheme = 'light';
      }
    } catch(e) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased selection:bg-blue-600 selection:text-white transition-colors duration-300">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
