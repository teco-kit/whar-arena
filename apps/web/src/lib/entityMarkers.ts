export const markerShapes = [
  "circle",
  "square",
  "triangle",
  "diamond",
  "star",
  "pentagon",
  "hexagon",
  "crescent",
  "quatrefoil",
  "pacman",
] as const;
export const modelMarkerColors = [
  "#b35806",
  "#6d597a",
  "#2a9d8f",
  "#c1121f",
  "#1d5f91",
  "#b5179e",
  "#e76f51",
  "#588157",
  "#7f5539",
  "#4361ee",
  "#9c6644",
  "#457b9d",
] as const;
export const datasetMarkerColors = [
  "#0077b6",
  "#2b9348",
  "#5a189a",
  "#d00000",
  "#ee9b00",
  "#0081a7",
  "#6a994e",
  "#9d4edd",
  "#bc6c25",
  "#3a86ff",
  "#8338ec",
  "#d9485f",
] as const;

export type MarkerShape = (typeof markerShapes)[number];
export type MarkerPalette = "model" | "dataset";

export type EntityMarker = {
  color: string;
  shape: MarkerShape;
};

function hashId(id: string) {
  let hash = 2166136261;
  for (let index = 0; index < id.length; index += 1) {
    hash ^= id.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export function getEntityMarker(
  id: string,
  index?: number,
  palette: MarkerPalette = "model",
): EntityMarker {
  const hash = hashId(id);
  const markerIndex = index ?? hash;
  const colors = palette === "dataset" ? datasetMarkerColors : modelMarkerColors;
  return {
    shape: markerShapes[markerIndex % markerShapes.length],
    color: colors[markerIndex % colors.length],
  };
}

// Shapes are optically normalized to roughly 120 square units of filled area.
export const markerCircleRadius = 6.2;
export const markerSquareHalfSize = 5.5;
export const markerTrianglePoints = "0,-8.04 8.04,6.89 -8.04,6.89";
export const markerDiamondPoints = "0,-7.75 7.75,0 0,7.75 -7.75,0";
export const markerStarPoints =
  "0,-9.03 2.66,-3.65 8.59,-2.79 4.3,1.39 5.3,7.3 0,4.52 -5.3,7.3 -4.3,1.39 -8.59,-2.79 -2.66,-3.65";
export const markerPentagonPoints = "0,-7.11 6.76,-2.19 4.17,5.74 -4.17,5.74 -6.76,-2.19";
export const markerHexagonPoints = "-6.33,-3.17 0,-6.33 6.33,-3.17 6.33,3.17 0,6.33 -6.33,3.17";
export const markerCrescentPath =
  "M -8 -6 C -7 2.5 -4.5 8 0 8 C 4.5 8 7 2.5 8 -6 C 5 -1.2 2.2 1 0 1 C -2.2 1 -5 -1.2 -8 -6 Z";
export const markerQuatrefoilPath =
  "M 0 -8 C 2.7 -8 4.2 -6.3 4.2 -4.2 C 6.3 -4.2 8 -2.7 8 0 C 8 2.7 6.3 4.2 4.2 4.2 C 4.2 6.3 2.7 8 0 8 C -2.7 8 -4.2 6.3 -4.2 4.2 C -6.3 4.2 -8 2.7 -8 0 C -8 -2.7 -6.3 -4.2 -4.2 -4.2 C -4.2 -6.3 -2.7 -8 0 -8 Z";
export const markerPacmanPath = "M 0 0 L 6.06 -3.5 A 7 7 0 1 0 6.06 3.5 Z";
