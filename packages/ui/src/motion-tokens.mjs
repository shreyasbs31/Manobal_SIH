export const MOTION = {
  instant: { duration: 120, easing: "ease-out" },
  quick: { duration: 200, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" },
  settle: { duration: 320, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
  draw: { duration: 900, easing: "cubic-bezier(0.65, 0, 0.35, 1)" },
  breath: { duration: 4000, easing: "ease-in-out" },
};

export function motionToOpacityOnly(reduced, name) {
  if (reduced) {
    return { duration: MOTION.instant.duration, easing: "ease" };
  }
  return MOTION[name];
}
