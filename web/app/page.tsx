import Link from "next/link";

const FEATURED = [
  { code: "NK", name: "Spirit Airlines", blurb: "Marquee demo — GTF, merger block, Ch 11" },
  { code: "B6", name: "JetBlue Airways", blurb: "The blocked acquirer" },
  { code: "F9", name: "Frontier Airlines", blurb: "ULCC competitor watching Spirit" },
  { code: "WN", name: "Southwest Airlines", blurb: "Newark exit case study" },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="text-4xl font-bold">NetSim</h1>
      <p className="mt-2 text-lg text-gray-400">
        Outside-in airline network intelligence. Ask in plain English what a US carrier&apos;s
        network did and why.
      </p>

      <h2 className="mt-12 text-xl font-semibold">Featured carriers</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {FEATURED.map((c) => (
          <Link
            key={c.code}
            href={`/airline/${c.code}`}
            className="rounded-lg border border-gray-800 p-4 hover:border-gray-600"
          >
            <div className="font-mono text-sm text-gray-500">{c.code}</div>
            <div className="text-lg font-semibold">{c.name}</div>
            <div className="mt-1 text-sm text-gray-400">{c.blurb}</div>
          </Link>
        ))}
      </div>
    </main>
  );
}
