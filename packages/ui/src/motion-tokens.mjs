export const MOTION = {
  instant: { duration: 120, easing: "ease-out" },
  quick: { duration: 200, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" },
  settle: { duration: 320, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
  draw: { duration: 900, easing: "cubic-bezier(0.65, 0, 0.35, 1)" },
  breath: { duration: 4000, easing: "ease-in-out" },
};

export const BOX_BREATH_PATTERN = [
  { id: "in", label: "Breathe in", ms: 4000, expand: true, hold: false },
  { id: "hold-in", label: "Hold", ms: 4000, expand: true, hold: true },
  { id: "out", label: "Breathe out", ms: 4000, expand: false, hold: false },
  { id: "hold-out", label: "Hold", ms: 4000, expand: false, hold: true },
];

export const FOUR_SEVEN_EIGHT_PATTERN = [
  { id: "in", label: "Breathe in", ms: 4000, expand: true, hold: false },
  { id: "hold-in", label: "Hold", ms: 7000, expand: true, hold: true },
  { id: "out", label: "Breathe out", ms: 8000, expand: false, hold: false },
];

export const BREATH_SCALE_MIN = 0.86;
export const BREATH_SCALE_MAX = 1.12;

function breathSteps(pattern) {
  return pattern && pattern.length ? pattern : BOX_BREATH_PATTERN;
}

function breathTotal(steps) {
  return steps.reduce((sum, item) => sum + item.ms, 0) || 1;
}

export function breathPhaseAt(elapsedMs, pattern) {
  const steps = breathSteps(pattern);
  const total = breathTotal(steps);
  let t = elapsedMs % total;
  if (t < 0) {
    t += total;
  }
  for (let index = 0; index < steps.length; index += 1) {
    const item = steps[index];
    if (t < item.ms) {
      return {
        id: item.id,
        label: item.label,
        ms: item.ms,
        expand: item.expand,
        hold: item.hold,
        index,
        count: Math.max(1, Math.ceil((item.ms - t) / 1000)),
      };
    }
    t -= item.ms;
  }
  const first = steps[0];
  return {
    id: first.id,
    label: first.label,
    ms: first.ms,
    expand: first.expand,
    hold: first.hold,
    index: 0,
    count: Math.max(1, Math.ceil(first.ms / 1000)),
  };
}

export function breathScaleAt(elapsedMs, pattern, min = BREATH_SCALE_MIN, max = BREATH_SCALE_MAX) {
  const steps = breathSteps(pattern);
  const total = breathTotal(steps);
  let t = elapsedMs % total;
  if (t < 0) {
    t += total;
  }
  for (let index = 0; index < steps.length; index += 1) {
    const item = steps[index];
    if (t >= item.ms) {
      t -= item.ms;
      continue;
    }
    if (item.hold || item.ms <= 0) {
      return item.expand ? max : min;
    }
    const progress = Math.min(1, Math.max(0, t / item.ms));
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * progress);
    if (item.expand) {
      return min + (max - min) * eased;
    }
    return max - (max - min) * eased;
  }
  return min;
}

export function motionToOpacityOnly(reduced, name) {
  if (reduced) {
    return { duration: MOTION.instant.duration, easing: "ease" };
  }
  return MOTION[name];
}
