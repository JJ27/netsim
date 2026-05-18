const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Route = {
  o: string;
  d: string;
  seats: number;
  departures: number;
  passengers: number;
  distance_mi: number;
};

export type FleetEntry = {
  aircraft_type: number;
  departures: number;
  seats: number;
};

export type NetworkResponse = {
  carrier: string;
  period: string;
  routes: Route[];
  fleet: FleetEntry[];
};

export async function fetchNetwork(
  carrier: string,
  year: number,
  quarter: number
): Promise<NetworkResponse> {
  const r = await fetch(`${API}/network/${carrier}?year=${year}&quarter=${quarter}`);
  if (!r.ok) throw new Error(`network fetch failed: ${r.status}`);
  return r.json();
}

export type ChatRequest = {
  message: string;
  carrier?: string;
  year?: number;
  quarter?: number;
};

export type ChatResponse = Record<string, string>;

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const r = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) throw new Error(`chat failed: ${r.status}`);
  return r.json();
}
