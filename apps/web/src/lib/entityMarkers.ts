export const modelMarkerShapes = [
  "circle", "triangle", "pentagon", "heptagon", "rectangle", "parallelogram", "ellipse", "cross",
  "pentagram", "crown", "heart", "arrow", "crescent", "arc", "quatrefoil",
] as const;

export const datasetMarkerShapes = [
  "square", "hexagon", "trapezium", "rhombus", "superellipse", "drop", "diamond",
  "shield", "trefoil", "ring", "flower", "pinion", "semicircle", "pacman",
] as const;

export const markerShapes = [...modelMarkerShapes, ...datasetMarkerShapes] as const;

export const modelMarkerColors = [
  "#b35806", "#6d597a", "#2a9d8f", "#c1121f", "#1d5f91", "#b5179e",
  "#e76f51", "#588157", "#7f5539", "#4361ee", "#9c6644", "#457b9d",
] as const;
export const datasetMarkerColors = [
  "#0077b6", "#2b9348", "#5a189a", "#d00000", "#ee9b00", "#0081a7",
  "#6a994e", "#9d4edd", "#bc6c25", "#3a86ff", "#8338ec", "#d9485f",
] as const;

export type MarkerShape = (typeof markerShapes)[number];
export type MarkerPalette = "model" | "dataset";
export type EntityMarker = { color: string; shape: MarkerShape };

const shapePaths: Record<MarkerShape, string> = {
  circle: "M 0 -6.2 A 6.2 6.2 0 1 1 0 6.2 A 6.2 6.2 0 1 1 0 -6.2 Z",
  triangle: "M 0 -8.04 L 8.04 6.89 L -8.04 6.89 Z",
  square: "M -5.5 -5.5 H 5.5 V 5.5 H -5.5 Z",
  pentagon: "M 0 -7.11 L 6.76 -2.19 L 4.17 5.74 L -4.17 5.74 L -6.76 -2.19 Z",
  hexagon: "M -6.33 -3.17 L 0 -6.33 L 6.33 -3.17 L 6.33 3.17 L 0 6.33 L -6.33 3.17 Z",
  heptagon: "M 0 -7.1 L 5.55 -4.43 L 6.92 1.58 L 3.08 6.4 L -3.08 6.4 L -6.92 1.58 L -5.55 -4.43 Z",
  rectangle: "M -8 -4.2 H 8 V 4.2 H -8 Z",
  trapezium: "M -5.2 -5.8 H 5.2 L 8 5.8 H -8 Z",
  parallelogram: "M -4.8 -5.7 H 8 L 4.8 5.7 H -8 Z",
  rhombus: "M 0 -6.5 L 8 0 L 0 6.5 L -8 0 Z",
  ellipse: "M 0 -4.8 A 8 4.8 0 1 1 0 4.8 A 8 4.8 0 1 1 0 -4.8 Z",
  superellipse: "M -3.5 -6.3 C -5.8 -6.3 -6.8 -5.3 -6.8 -3 V 3 C -6.8 5.3 -5.8 6.3 -3.5 6.3 H 3.5 C 5.8 6.3 6.8 5.3 6.8 3 V -3 C 6.8 -5.3 5.8 -6.3 3.5 -6.3 Z",
  cross: "M -2.4 -7.5 H 2.4 V -2.4 H 7.5 V 2.4 H 2.4 V 7.5 H -2.4 V 2.4 H -7.5 V -2.4 H -2.4 Z",
  pentagram: "M 0 -9.03 L 2.66 -3.65 L 8.59 -2.79 L 4.3 1.39 L 5.3 7.3 L 0 4.52 L -5.3 7.3 L -4.3 1.39 L -8.59 -2.79 L -2.66 -3.65 Z",
  crown: "M -8 -5 L -4 3 L 0 -3 L 4 3 L 8 -5 L 6.2 6 H -6.2 Z",
  heart: "M 0 7.8 C -1.3 6.4 -7.3 2.6 -7.3 -2.4 C -7.3 -6.7 -2 -8 0 -4.5 C 2 -8 7.3 -6.7 7.3 -2.4 C 7.3 2.6 1.3 6.4 0 7.8 Z",
  drop: "M 0 -8.5 C 2.2 -5.2 6.2 -1.2 6.2 2.6 A 6.2 6.2 0 1 1 -6.2 2.6 C -6.2 -1.2 -2.2 -5.2 0 -8.5 Z",
  arrow: "M -2.5 7.5 V 0.5 H -7 L 0 -8 L 7 0.5 H 2.5 V 7.5 Z",
  diamond: "M 0 -7.75 L 7.75 0 L 0 7.75 L -7.75 0 Z",
  crescent: "M -8 -6 C -7 2.5 -4.5 8 0 8 C 4.5 8 7 2.5 8 -6 C 5 -1.2 2.2 1 0 1 C -2.2 1 -5 -1.2 -8 -6 Z",
  shield: "M 0 -8 L 7 -5.2 V -0.5 C 7 3.7 4.2 6.6 0 8.5 C -4.2 6.6 -7 3.7 -7 -0.5 V -5.2 Z",
  arc: "M -8 5 A 8 8 0 0 1 8 5 H 4.2 A 4.2 4.2 0 0 0 -4.2 5 Z",
  trefoil: "M 0 -1 C -5 -8 -10 -1 -5 3 C -3 4.6 -1.2 3.5 0 2 C 1.2 3.5 3 4.6 5 3 C 10 -1 5 -8 0 -1 Z",
  quatrefoil: "M 0 -8 C 2.7 -8 4.2 -6.3 4.2 -4.2 C 6.3 -4.2 8 -2.7 8 0 C 8 2.7 6.3 4.2 4.2 4.2 C 4.2 6.3 2.7 8 0 8 C -2.7 8 -4.2 6.3 -4.2 4.2 C -6.3 4.2 -8 2.7 -8 0 C -8 -2.7 -6.3 -4.2 -4.2 -4.2 C -4.2 -6.3 -2.7 -8 0 -8 Z",
  ring: "M 0 -8 A 8 8 0 1 1 0 8 A 8 8 0 1 1 0 -8 Z M 0 -3.5 A 3.5 3.5 0 1 0 0 3.5 A 3.5 3.5 0 1 0 0 -3.5 Z",
  flower: "M 0 -3 C -5 -9 -10 -3 -5 1 C -10 5 -3 10 0 4 C 3 10 10 5 5 1 C 10 -3 5 -9 0 -3 Z M 0 -1.8 A 1.8 1.8 0 1 0 0 1.8 A 1.8 1.8 0 1 0 0 -1.8 Z",
  pinion: "M 0 -8 L 2 -6 L 4.8 -6.3 L 5.5 -3.5 L 8 -2 L 6.8 0 L 8 2 L 5.5 3.5 L 4.8 6.3 L 2 6 L 0 8 L -2 6 L -4.8 6.3 L -5.5 3.5 L -8 2 L -6.8 0 L -8 -2 L -5.5 -3.5 L -4.8 -6.3 L -2 -6 Z M 0 -3 A 3 3 0 1 0 0 3 A 3 3 0 1 0 0 -3 Z",
  semicircle: "M -8 -2 H 8 A 8 8 0 0 1 -8 -2 Z",
  pacman: "M 0 0 L 6.06 -3.5 A 7 7 0 1 0 6.06 3.5 Z",
};

export function getMarkerPath(shape: MarkerShape) {
  return shapePaths[shape];
}

function hashId(id: string) {
  let hash = 2166136261;
  for (let index = 0; index < id.length; index += 1) {
    hash ^= id.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export function getEntityMarker(id: string, index?: number, palette: MarkerPalette = "model"): EntityMarker {
  const markerIndex = index ?? hashId(id);
  const shapes = palette === "dataset" ? datasetMarkerShapes : modelMarkerShapes;
  const colors = palette === "dataset" ? datasetMarkerColors : modelMarkerColors;
  const shape = shapes[markerIndex % shapes.length];
  return { shape, color: colors[markerIndex % colors.length] };
}
