"use client";

import { useEffect, useState } from "react";
import NetworkMap from "@/components/NetworkMap";
import ChatPanel from "@/components/ChatPanel";
import TimeScrubber from "@/components/TimeScrubber";
import { fetchNetwork, NetworkResponse } from "@/lib/api";

export default function AirlinePage({ params }: { params: Promise<{ code: string }> }) {
  const [code, setCode] = useState<string>("");
  const [year, setYear] = useState(2024);
  const [quarter, setQuarter] = useState(3);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    params.then((p) => setCode(p.code.toUpperCase()));
  }, [params]);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    fetchNetwork(code, year, quarter)
      .then(setNetwork)
      .finally(() => setLoading(false));
  }, [code, year, quarter]);

  return (
    <div className="grid h-screen grid-cols-[1fr_420px]">
      <div className="relative">
        <NetworkMap network={network} />
        <div className="absolute bottom-4 left-4 right-4">
          <TimeScrubber
            year={year}
            quarter={quarter}
            onChange={(y, q) => {
              setYear(y);
              setQuarter(q);
            }}
          />
        </div>
        <div className="absolute left-4 top-4 rounded bg-panel/80 px-3 py-2 backdrop-blur">
          <div className="font-mono text-xs text-gray-500">{code}</div>
          <div className="text-lg font-semibold">
            {network?.period ?? `${year}Q${quarter}`}
            {loading && <span className="ml-2 text-xs text-gray-500">loading…</span>}
          </div>
          <div className="text-xs text-gray-400">
            {network ? `${network.routes.length} routes` : ""}
          </div>
        </div>
      </div>
      <ChatPanel carrier={code} year={year} quarter={quarter} />
    </div>
  );
}
