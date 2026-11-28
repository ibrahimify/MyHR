"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem("myhr-theme");
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const selected = initialTheme();
    document.documentElement.dataset.theme = selected;
    const frame = window.requestAnimationFrame(() => setTheme(selected));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function selectTheme(nextTheme: Theme) {
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem("myhr-theme", nextTheme);
  }

  return (
    <div className="theme-toggle" aria-label="Color theme">
      <button
        aria-label="Use light theme"
        aria-pressed={theme === "light"}
        onClick={() => selectTheme("light")}
        title="Light theme"
        type="button"
      >
        <Sun size={16} />
      </button>
      <button
        aria-label="Use dark theme"
        aria-pressed={theme === "dark"}
        onClick={() => selectTheme("dark")}
        title="Dark theme"
        type="button"
      >
        <Moon size={16} />
      </button>
    </div>
  );
}
