"use client";

import { useEffect, useState } from "react";

export function useTimer(resetTrigger: number): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setElapsed(0);
    const interval = window.setInterval(() => {
      setElapsed((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(interval);
  }, [resetTrigger]);

  return elapsed;
}

