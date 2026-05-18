"use client";

type Props = {
  year: number;
  quarter: number;
  onChange: (year: number, quarter: number) => void;
};

const MIN_YEAR = 2018;
const MAX_YEAR = 2025;

export default function TimeScrubber({ year, quarter, onChange }: Props) {
  const totalQuarters = (MAX_YEAR - MIN_YEAR + 1) * 4;
  const idx = (year - MIN_YEAR) * 4 + (quarter - 1);

  function setIdx(i: number) {
    const y = MIN_YEAR + Math.floor(i / 4);
    const q = (i % 4) + 1;
    onChange(y, q);
  }

  return (
    <div className="rounded-lg bg-panel/80 px-4 py-3 backdrop-blur">
      <div className="mb-2 flex items-center justify-between text-xs text-gray-400">
        <span>{MIN_YEAR}Q1</span>
        <span className="font-mono text-sm text-gray-200">
          {year}Q{quarter}
        </span>
        <span>{MAX_YEAR}Q4</span>
      </div>
      <input
        type="range"
        min={0}
        max={totalQuarters - 1}
        value={idx}
        onChange={(e) => setIdx(Number(e.target.value))}
        className="w-full"
      />
    </div>
  );
}
