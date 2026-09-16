import type { ReactElement, SVGProps } from "react";

const ink = "#1B2427";
const neemFill = "rgba(47,93,80,0.20)";
const dawnFill = "rgba(242,198,160,0.30)";
const mistFill = "#F4F8F6";

type SceneProps = SVGProps<SVGSVGElement>;

function Frame({
  title,
  children,
  ...props
}: SceneProps & { title: string; children: ReactElement | ReactElement[] }) {
  return (
    <svg
      role="img"
      viewBox="0 0 160 120"
      fill="none"
      stroke={ink}
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <title>{title}</title>
      {children}
    </svg>
  );
}

export function SceneBunkDawn(props: SceneProps) {
  return (
    <Frame title="After night duty, tea by a dawn window" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <rect fill={dawnFill} height="40" stroke="none" width="36" x="108" y="14" />
      <rect height="40" width="36" x="108" y="14" />
      <path d="M108 34 H144" />
      <path d="M126 14 V54" />
      <path d="M18 96 H142" />
      <rect height="18" width="70" x="22" y="78" />
      <circle cx="48" cy="58" r="8" />
      <path d="M36 92 C36 74 40 70 48 70 C56 70 60 74 60 92" />
      <path d="M78 86 C78 82 82 80 86 82" fill={neemFill} />
      <ellipse cx="82" cy="86" rx="8" ry="4" />
    </Frame>
  );
}

export function SceneHighPost(props: SceneProps) {
  return (
    <Frame title="A high post at dusk" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M4 78 L40 36 L72 70 L104 28 L156 78" fill={neemFill} />
      <rect fill={dawnFill} height="18" width="28" x="86" y="70" />
      <rect height="18" width="28" x="86" y="70" />
      <path d="M86 70 L100 56 L114 70" />
    </Frame>
  );
}

export function SceneJungleCamp(props: SceneProps) {
  return (
    <Frame title="A jungle camp in soft rain" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M20 96 C20 40 50 24 50 24 C50 24 80 40 80 96" fill={neemFill} />
      <path d="M90 96 C90 48 118 30 118 30 C118 30 142 48 142 96" fill={neemFill} />
      <path d="M54 96 L80 70 L106 96" />
      <path d="M70 28 L72 36 M90 22 L92 30 M110 26 L112 34" />
    </Frame>
  );
}

export function SceneCityNight(props: SceneProps) {
  return (
    <Frame title="Night duty by a street light" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M20 96 H140" />
      <path d="M36 96 V60 H124 V96" />
      <circle cx="80" cy="40" r="8" fill={dawnFill} />
      <path d="M80 48 V70" />
      <circle cx="64" cy="78" r="6" />
      <path d="M56 96 C56 84 64 80 64 80 C64 80 72 84 72 96" />
      <ellipse cx="96" cy="90" rx="7" ry="3" />
    </Frame>
  );
}

export function SceneFamilyCall(props: SceneProps) {
  return (
    <Frame title="A video call with family" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <rect height="48" width="40" x="96" y="28" />
      <circle cx="116" cy="44" r="6" fill={dawnFill} />
      <path d="M106 70 C106 60 116 56 116 56 C116 56 126 60 126 70" />
      <circle cx="52" cy="52" r="8" />
      <path d="M38 96 C38 74 52 68 52 68 C52 68 66 74 66 96" />
    </Frame>
  );
}

export function SceneBuddyTea(props: SceneProps) {
  return (
    <Frame title="Two colleagues sharing tea" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M24 96 H136" />
      <circle cx="56" cy="54" r="7" />
      <circle cx="104" cy="54" r="7" />
      <path d="M42 96 C42 76 56 70 56 70 C56 70 70 76 70 96" fill={neemFill} />
      <path d="M90 96 C90 76 104 70 104 70 C104 70 118 76 118 96" fill={neemFill} />
      <ellipse cx="78" cy="86" rx="10" ry="4" />
    </Frame>
  );
}

export function SceneSleepWindDown(props: SceneProps) {
  return (
    <Frame title="Listening with eyes closed" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <circle cx="80" cy="52" r="14" />
      <path d="M68 52 Q80 48 92 52" />
      <path d="M54 58 Q48 52 54 46 M106 58 Q112 52 106 46" />
      <path d="M58 96 C58 78 80 72 80 72 C80 72 102 78 102 96" fill={neemFill} />
    </Frame>
  );
}

export function SceneInformalWalk(props: SceneProps) {
  return (
    <Frame title="A welfare officer and a jawan walking" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M16 96 H144" />
      <circle cx="64" cy="50" r="7" />
      <circle cx="96" cy="48" r="7" />
      <path d="M54 96 C54 74 64 68 64 68 C64 68 74 74 74 96" fill={neemFill} />
      <path d="M86 96 C86 72 96 66 96 66 C96 66 106 72 106 96" />
    </Frame>
  );
}

export function SceneCounsellorCall(props: SceneProps) {
  return (
    <Frame title="A counsellor on a laptop call" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <circle cx="80" cy="44" r="8" />
      <path d="M64 88 C64 68 80 62 80 62 C80 62 96 68 96 88" fill={neemFill} />
      <rect height="14" width="40" x="60" y="84" />
      <path d="M70 84 V78 H90 V84" />
    </Frame>
  );
}

export function SceneLeaveWindow(props: SceneProps) {
  return (
    <Frame title="A leave window and a bus in the distance" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <rect height="56" width="48" x="24" y="28" />
      <path d="M24 44 H72" />
      <circle cx="48" cy="64" r="10" fill={dawnFill} />
      <rect height="16" width="36" x="100" y="78" />
      <circle cx="110" cy="96" r="4" />
      <circle cx="126" cy="96" r="4" />
    </Frame>
  );
}

export function SceneShiftMoon(props: SceneProps) {
  return (
    <Frame title="Barracks at night under a moon" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M118 28 A12 12 0 1 0 130 48" fill={dawnFill} />
      <rect height="28" width="90" x="28" y="64" />
      <path d="M28 64 L73 44 L118 64" />
      <rect height="12" width="10" x="70" y="80" />
    </Frame>
  );
}

export function SceneOnboardingPhone(props: SceneProps) {
  return (
    <Frame title="Hands holding a phone with a contour" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <rect height="56" rx="6" width="32" x="64" y="28" />
      <path d="M70 44 C74 38 78 38 82 44 S90 52 94 44" />
      <path d="M48 96 C52 80 64 76 64 76" />
      <path d="M112 96 C108 80 96 76 96 76" />
    </Frame>
  );
}

export function SceneEmptyPath(props: SceneProps) {
  return (
    <Frame title="A quiet path through hills" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <path d="M4 86 C36 70 60 92 90 74 C120 58 148 78 156 70" fill={neemFill} />
      <path d="M20 100 C48 92 80 104 120 94" />
    </Frame>
  );
}

export function SceneCircleSupport(props: SceneProps) {
  return (
    <Frame title="A group sitting in a circle outdoors" {...props}>
      <rect fill={mistFill} height="118" stroke="none" width="158" x="1" y="1" />
      <ellipse cx="80" cy="78" rx="40" ry="14" />
      <circle cx="80" cy="50" r="6" />
      <circle cx="52" cy="62" r="6" />
      <circle cx="108" cy="62" r="6" />
      <circle cx="60" cy="86" r="6" />
      <circle cx="100" cy="86" r="6" />
    </Frame>
  );
}

export const ILLUSTRATION_SLOTS = [
  "bunkDawn",
  "highPost",
  "jungleCamp",
  "cityNight",
  "familyCall",
  "buddyTea",
  "sleepWindDown",
  "informalWalk",
  "counsellorCall",
  "leaveWindow",
  "shiftMoon",
  "onboardingPhone",
  "emptyPath",
  "circleSupport",
] as const;

export type IllustrationSlot = (typeof ILLUSTRATION_SLOTS)[number];

export const illustrations: Record<
  IllustrationSlot,
  (props: SceneProps) => ReactElement
> = {
  bunkDawn: SceneBunkDawn,
  highPost: SceneHighPost,
  jungleCamp: SceneJungleCamp,
  cityNight: SceneCityNight,
  familyCall: SceneFamilyCall,
  buddyTea: SceneBuddyTea,
  sleepWindDown: SceneSleepWindDown,
  informalWalk: SceneInformalWalk,
  counsellorCall: SceneCounsellorCall,
  leaveWindow: SceneLeaveWindow,
  shiftMoon: SceneShiftMoon,
  onboardingPhone: SceneOnboardingPhone,
  emptyPath: SceneEmptyPath,
  circleSupport: SceneCircleSupport,
};
