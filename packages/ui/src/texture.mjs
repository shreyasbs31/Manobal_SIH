/**
 * Seeded contour texture: simplex-style noise plus marching squares.
 * Used behind the Lay ribbon, voice contour, onboarding, and the safety screen.
 */

const GRAD = [
  [1, 1],
  [-1, 1],
  [1, -1],
  [-1, -1],
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

function permTable(seed) {
  const p = new Uint8Array(512);
  const source = new Uint8Array(256);
  for (let i = 0; i < 256; i += 1) {
    source[i] = i;
  }
  let state = seed >>> 0 || 1;
  const rand = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state;
  };
  for (let i = 255; i > 0; i -= 1) {
    const j = rand() % (i + 1);
    const current = source[i];
    source[i] = source[j];
    source[j] = current;
  }
  for (let i = 0; i < 512; i += 1) {
    p[i] = source[i & 255];
  }
  return p;
}

function dot(ix, gx, gy) {
  const g = GRAD[ix & 7];
  return g[0] * gx + g[1] * gy;
}

function fade(t) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function simplex2(x, y, perm) {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const xf = x - x0;
  const yf = y - y0;
  const u = fade(xf);
  const v = fade(yf);
  const aa = perm[perm[x0 & 255] + (y0 & 255)];
  const ab = perm[perm[x0 & 255] + ((y0 + 1) & 255)];
  const ba = perm[perm[(x0 + 1) & 255] + (y0 & 255)];
  const bb = perm[perm[(x0 + 1) & 255] + ((y0 + 1) & 255)];
  const x1 = lerp(dot(aa, xf, yf), dot(ba, xf - 1, yf), u);
  const x2 = lerp(dot(ab, xf, yf - 1), dot(bb, xf - 1, yf - 1), u);
  return lerp(x1, x2, v);
}

export function hashSeed(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

const EDGE = [
  [],
  [[3, 0]],
  [[0, 1]],
  [[3, 1]],
  [[1, 2]],
  [
    [3, 0],
    [1, 2],
  ],
  [[0, 2]],
  [[3, 2]],
  [[2, 3]],
  [[2, 0]],
  [
    [0, 1],
    [2, 3],
  ],
  [[1, 2]],
  [[0, 3]],
  [[0, 1]],
  [[3, 0]],
  [],
];

function interp(x0, y0, x1, y1, v0, v1, iso) {
  const t = Math.abs(v1 - v0) < 1e-6 ? 0.5 : (iso - v0) / (v1 - v0);
  return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t];
}

function edgePoint(edge, x, y, cellW, cellH, values, iso) {
  const [v00, v10, v11, v01] = values;
  if (edge === 0) {
    return interp(x, y, x + cellW, y, v00, v10, iso);
  }
  if (edge === 1) {
    return interp(x + cellW, y, x + cellW, y + cellH, v10, v11, iso);
  }
  if (edge === 2) {
    return interp(x, y + cellH, x + cellW, y + cellH, v01, v11, iso);
  }
  return interp(x, y, x, y + cellH, v00, v01, iso);
}

export function contourPaths(options) {
  const width = options.width ?? 390;
  const height = options.height ?? 220;
  const cols = options.cols ?? 28;
  const rows = options.rows ?? 16;
  const levels = Math.min(9, Math.max(6, options.levels ?? 7));
  const perm = permTable(hashSeed(options.seed));
  const cellW = width / cols;
  const cellH = height / rows;
  const field = [];
  for (let y = 0; y <= rows; y += 1) {
    const row = [];
    for (let x = 0; x <= cols; x += 1) {
      const nx = x * 0.22 + 0.3;
      const ny = y * 0.22 + 0.15;
      const dx = x / cols - 0.5;
      const dy = y / rows - 0.5;
      const radial = Math.hypot(dx * 1.4, dy);
      row.push(simplex2(nx, ny, perm) * 0.65 + radial);
    }
    field.push(row);
  }
  const paths = [];
  for (let levelIndex = 0; levelIndex < levels; levelIndex += 1) {
    const iso = 0.12 + (levelIndex / Math.max(levels - 1, 1)) * 0.7;
    const segments = [];
    for (let y = 0; y < rows; y += 1) {
      for (let x = 0; x < cols; x += 1) {
        const v00 = field[y][x];
        const v10 = field[y][x + 1];
        const v11 = field[y + 1][x + 1];
        const v01 = field[y + 1][x];
        const idx =
          (v00 > iso ? 1 : 0) +
          (v10 > iso ? 2 : 0) +
          (v11 > iso ? 4 : 0) +
          (v01 > iso ? 8 : 0);
        const edges = EDGE[idx];
        for (const pair of edges) {
          const a = edgePoint(pair[0], x * cellW, y * cellH, cellW, cellH, [v00, v10, v11, v01], iso);
          const b = edgePoint(pair[1], x * cellW, y * cellH, cellW, cellH, [v00, v10, v11, v01], iso);
          segments.push(
            `M ${a[0].toFixed(1)} ${a[1].toFixed(1)} L ${b[0].toFixed(1)} ${b[1].toFixed(1)}`,
          );
        }
      }
    }
    if (segments.length > 0) {
      paths.push({ d: segments.join(" "), level: levelIndex });
    }
  }
  return paths;
}

export function contourSvg(seed, width = 390, height = 220) {
  const paths = contourPaths({ seed, width, height });
  const body = paths
    .map(
      (path) =>
        `<path d="${path.d}" fill="none" stroke="currentColor" stroke-width="1" />`,
    )
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" aria-hidden="true">${body}</svg>`;
}
