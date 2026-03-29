import Link from "next/link";

const links = [
  { href: "/admin/import", label: "Import" },
  { href: "/admin/students", label: "Students" },
  { href: "/admin/simulate", label: "Simulate" },
  { href: "/admin/difficulty", label: "Difficulty" },
  { href: "/admin/export", label: "Export" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Admin</p>
        <h1 className="font-heading text-5xl text-ink">Manage imports, synthetic data, difficulty, and exports.</h1>
      </div>
      <nav className="mb-8 flex flex-wrap gap-3">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-full border border-ink/10 bg-white/70 px-4 py-2 text-sm font-semibold text-ink transition hover:border-clay"
          >
            {link.label}
          </Link>
        ))}
      </nav>
      {children}
    </main>
  );
}

