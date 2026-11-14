"use client";

import { motion } from "framer-motion";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center bg-white px-6 text-center dark:bg-black">
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="text-4xl font-semibold tracking-tight text-black sm:text-5xl dark:text-zinc-50"
      >
        MyHR
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
        className="mt-4 max-w-md text-base text-zinc-600 dark:text-zinc-400"
      >
        Employee management for government-like organizations. Web version in
        progress.
      </motion.p>
    </main>
  );
}
