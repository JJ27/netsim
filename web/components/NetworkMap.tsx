"use client";

import { useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { ArcLayer, ScatterplotLayer } from "@deck.gl/layers";
import Map from "react-map-gl/mapbox";
import "mapbox-gl/dist/mapbox-gl.css";
import type { NetworkResponse } from "@/lib/api";
import { AIRPORT_COORDS } from "@/lib/airports";

const INITIAL_VIEW = {
  longitude: -96,
  latitude: 38,
  zoom: 3.5,
  pitch: 30,
  bearing: 0,
};

type Props = { network: NetworkResponse | null };

export default function NetworkMap({ network }: Props) {
  const { arcs, points } = useMemo(() => {
    if (!network) return { arcs: [], points: [] };
    const arcs = network.routes
      .map((r) => {
        const o = AIRPORT_COORDS[r.o];
        const d = AIRPORT_COORDS[r.d];
        if (!o || !d) return null;
        return { source: o, target: d, departures: r.departures, seats: r.seats };
      })
      .filter(Boolean) as { source: [number, number]; target: [number, number]; departures: number; seats: number }[];

    const airports = new Set<string>();
    network.routes.forEach((r) => {
      airports.add(r.o);
      airports.add(r.d);
    });
    const points = [...airports]
      .map((iata) => AIRPORT_COORDS[iata])
      .filter(Boolean) as [number, number][];

    return { arcs, points };
  }, [network]);

  const layers = [
    new ArcLayer({
      id: "routes",
      data: arcs,
      getSourcePosition: (d: { source: [number, number] }) => d.source,
      getTargetPosition: (d: { target: [number, number] }) => d.target,
      getSourceColor: [255, 200, 80],
      getTargetColor: [255, 120, 60],
      getWidth: (d: { departures: number }) => Math.max(0.5, Math.log10(d.departures + 1)),
      getHeight: 0.4,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: "airports",
      data: points,
      getPosition: (d: [number, number]) => d,
      getFillColor: [255, 255, 255],
      getRadius: 3,
      radiusUnits: "pixels",
    }),
  ];

  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

  return (
    <DeckGL initialViewState={INITIAL_VIEW} controller layers={layers}>
      {token ? (
        <Map mapboxAccessToken={token} mapStyle="mapbox://styles/mapbox/dark-v11" />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-gray-500">
          Set NEXT_PUBLIC_MAPBOX_TOKEN to render base tiles.
        </div>
      )}
    </DeckGL>
  );
}
