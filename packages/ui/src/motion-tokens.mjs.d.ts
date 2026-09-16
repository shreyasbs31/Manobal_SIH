export const MOTION: {
  instant: { duration: number; easing: string };
  quick: { duration: number; easing: string };
  settle: { duration: number; easing: string };
  draw: { duration: number; easing: string };
  breath: { duration: number; easing: string };
};

export function motionToOpacityOnly(
  reduced: boolean,
  name: keyof typeof MOTION,
): { duration: number; easing: string };
