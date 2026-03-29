import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`surface-sheen motion-rise rounded-[2rem] border border-white/70 bg-white/82 p-6 shadow-soft backdrop-blur transition duration-300 ease-out hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(89,64,46,0.16)] ${className}`}
    >
      {children}
    </div>
  );
}
