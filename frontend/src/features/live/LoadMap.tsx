/**
 * Load map.
 *
 * MapLibre GL against OpenFreeMap tiles: no API key, no per-view billing.
 * The map is decoration for the facts, never a source of them, so a WebGL or
 * tile failure degrades to a coordinate list rather than blocking the screen.
 */

import maplibregl, {
  type GeoJSONSource,
  type Map as MapLibreMap,
  type StyleSpecification,
} from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import type { BoardRow } from "@/app/types";
import "maplibre-gl/dist/maplibre-gl.css";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const US_CENTER: [number, number] = [-93.5, 38.5];

interface LoadMapProps {
  rows: BoardRow[];
  selected: BoardRow | null;
  onSelect: (reference: string) => void;
}

function markerColor(row: BoardRow): string {
  switch (row.facts.classification) {
    case "late":
      return "#cf4035";
    case "at_risk":
      return "#a86a10";
    case "unknown":
      return "#8492a0";
    default:
      return "#12915f";
  }
}

export function LoadMap({ rows, selected, onSelect }: LoadMapProps) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!container.current || map.current) return;
    try {
      const instance = new maplibregl.Map({
        container: container.current,
        style: STYLE_URL as unknown as StyleSpecification | string,
        center: US_CENTER,
        zoom: 3.4,
        attributionControl: { compact: true },
      });
      instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
      instance.on("load", () => setReady(true));
      instance.on("error", () => setFailed(true));
      map.current = instance;
    } catch {
      setFailed(true);
    }
    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Position markers for every load that has reported one.
  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready) return;

    markers.current.forEach((marker) => marker.remove());
    markers.current = rows
      .filter((row) => row.facts.position)
      .map((row) => {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "mapdot";
        element.style.background = markerColor(row);
        element.setAttribute("aria-label", `${row.reference}, ${row.origin} to ${row.destination}`);
        if (row.reference === selected?.reference) element.classList.add("mapdot--active");
        element.addEventListener("click", () => onSelect(row.reference));
        return new maplibregl.Marker({ element })
          .setLngLat([row.facts.position!.longitude, row.facts.position!.latitude])
          .addTo(instance);
      });
  }, [rows, ready, selected?.reference, onSelect]);

  // Draw the selected load's remaining leg: current position to pickup.
  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready) return;

    const source = instance.getSource("selected-leg") as GeoJSONSource | undefined;
    const position = selected?.facts.position;
    const pickup = selected?.origin_point;

    const data = {
      // A two-point leg: where the truck is, and the pickup it is heading to.
      type: "FeatureCollection" as const,
      features:
        position && pickup
          ? [
              {
                type: "Feature" as const,
                properties: {},
                geometry: {
                  type: "LineString" as const,
                  coordinates: [
                    [position.longitude, position.latitude],
                    [pickup.longitude, pickup.latitude],
                  ],
                },
              },
            ]
          : [],
    };

    if (source) {
      source.setData(data);
    } else {
      instance.addSource("selected-leg", { type: "geojson", data });
      instance.addLayer({
        id: "selected-leg",
        type: "line",
        source: "selected-leg",
        layout: { "line-cap": "round" },
        paint: { "line-color": "#10a294", "line-width": 3, "line-dasharray": [2, 1.4] },
      });
    }

    if (position && pickup) {
      instance.fitBounds(
        [
          [
            Math.min(position.longitude, pickup.longitude),
            Math.min(position.latitude, pickup.latitude),
          ],
          [
            Math.max(position.longitude, pickup.longitude),
            Math.max(position.latitude, pickup.latitude),
          ],
        ],
        { padding: 90, maxZoom: 6.5, duration: 600 },
      );
    }
  }, [selected, ready]);

  if (failed) {
    return (
      <div className="map map--fallback">
        <p className="map__fallbackhead">Map unavailable</p>
        <ul className="map__coords">
          {rows.slice(0, 8).map((row) => (
            <li key={row.load_id}>
              <b>{row.reference}</b>{" "}
              {row.facts.position
                ? `${row.facts.position.latitude.toFixed(3)}, ${row.facts.position.longitude.toFixed(3)}`
                : "no position"}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return <div className="map" ref={container} aria-label="Load positions" role="img" />;
}
