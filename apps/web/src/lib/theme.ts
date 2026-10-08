"use client";

import { useEffect, useState } from "react";

export type ThemePreference = "dark" | "light" | "system";

const THEME_STORAGE_KEY = "arm_theme_preference";

export function getStoredTheme(): ThemePreference {
  if (typeof window === "undefined") return "system";
  try {
    const val = localStorage.getItem(THEME_STORAGE_KEY) as ThemePreference;
    if (val === "dark" || val === "light" || val === "system") {
      return val;
    }
  } catch {
    // LocalStorage unavailable
  }
  return "system";
}

export function applyTheme(theme: ThemePreference) {
  if (typeof window === "undefined") return;

  const root = document.documentElement;
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  const isDark = theme === "dark" || (theme === "system" && systemPrefersDark);

  if (isDark) {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }

  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage errors
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemePreference>("system");

  useEffect(() => {
    const stored = getStoredTheme();
    setTheme(stored);
    applyTheme(stored);

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (getStoredTheme() === "system") {
        applyTheme("system");
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const changeTheme = (newTheme: ThemePreference) => {
    setTheme(newTheme);
    applyTheme(newTheme);
  };

  return { theme, setTheme: changeTheme };
}
