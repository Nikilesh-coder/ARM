"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app/settings");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black text-zinc-500 font-mono text-xs">
      Redirecting to ARM Settings &amp; Integrations...
    </div>
  );
}
