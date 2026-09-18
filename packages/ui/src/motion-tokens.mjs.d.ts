export const MOTION: {
  instant: { duration: number; easing: string };
  quick: { duration: number; easing: string };
  settle: { duration: number; easing: string };
  draw: { duration: number; easing: string };
  breath: { duration: number; easing: string };
};

export type BreathPatternStep = {
  id: string;
  label: string;
  ms: number;
  expand: boolean;
  hold: boolean;
};

export const BOX_BREATH_PATTERN: BreathPatternStep[];
export const FOUR_SEVEN_EIGHT_PATTERN: BreathPatternStep[];

export const BREATH_SCALE_MIN: number;
export const BREATH_SCALE_MAX: number;

export function breathPhaseAt(
  elapsedMs: number,
  pattern?: BreathPatternStep[],
): BreathPatternStep & { index: number; count: number };

export function breathScaleAt(
  elapsedMs: number,
  pattern?: BreathPatternStep[],
  min?: number,
  max?: number,
): number;

export function motionToOpacityOnly(
  reduced: boolean,
  name: keyof typeof MOTION,
): { duration: number; easing: string };
