export interface ContourPath {
  d: string;
  level: number;
}

export function hashSeed(value: string): number;
export function simplex2(x: number, y: number): number;
export function contourPaths(options: {
  seed: string | number;
  width?: number;
  height?: number;
  cols?: number;
  rows?: number;
}): ContourPath[];
export function contourSvg(options: {
  seed: string | number;
  width?: number;
  height?: number;
}): string;
