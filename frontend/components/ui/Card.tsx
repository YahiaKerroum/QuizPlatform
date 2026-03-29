import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-[2rem] border border-white/60 bg-white/80 p-6 shadow-soft backdrop-blur ${className}`}>
      {children}
    </div>
  );
}

