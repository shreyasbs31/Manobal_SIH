import type { ReactElement, SVGProps } from "react";

import type { TierId } from "./types";

type IconProps = SVGProps<SVGSVGElement> & { title?: string | undefined };

function Svg({
  title,
  children,
  ...props
}: IconProps & { children: ReactElement | ReactElement[] }) {
  return (
    <svg
      aria-hidden={title ? undefined : true}
      fill="none"
      role={title ? "img" : undefined}
      viewBox="0 0 24 24"
      {...props}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

export function TierGlyph({
  tier,
  size = 18,
}: {
  tier: TierId;
  size?: number | undefined;
}) {
  const common = {
    fill: "currentColor",
    stroke: "var(--mb-text)",
    strokeWidth: 1.5,
  } as const;
  const label = {
    T0: "Tier 0, Steady",
    T1: "Tier 1, Watch",
    T2: "Tier 2, Elevated",
    T3: "Tier 3, High",
    T4: "Tier 4, Acute",
  }[tier];
  return (
    <svg
      aria-label={label}
      height={size}
      role="img"
      viewBox="0 0 20 20"
      width={size}
    >
      <title>{label}</title>
      {tier === "T0" ? <circle cx="10" cy="10" r="6.2" {...common} /> : null}
      {tier === "T1" ? (
        <path
          d="M10 2.8 C10 2.8 4.4 9.6 4.4 13.1 A5.6 5.6 0 0 0 15.6 13.1 C15.6 9.6 10 2.8 10 2.8 Z"
          {...common}
        />
      ) : null}
      {tier === "T2" ? <path d="M10 3.2 L17.2 16.4 H2.8 Z" {...common} /> : null}
      {tier === "T3" ? (
        <path d="M10 2.6 L17.4 10 L10 17.4 L2.6 10 Z" {...common} />
      ) : null}
      {tier === "T4" ? (
        <path d="M7.2 2.6 H12.8 L17.4 7.2 V12.8 L12.8 17.4 H7.2 L2.6 12.8 V7.2 Z" {...common} />
      ) : null}
    </svg>
  );
}

export function IconLayRibbon(props: IconProps) {
  return (
    <Svg title={props.title ?? "Your usual rhythm"} {...props}>
      <path
        d="M2 15 C6 8 9 8 12 12 S18 18 22 10"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
      <path
        d="M2 18 C6 12 9 12 12 15 S18 20 22 14"
        opacity="0.45"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </Svg>
  );
}

export function IconVoiceContour(props: IconProps) {
  return (
    <Svg title={props.title ?? "Voice"} {...props}>
      <ellipse cx="12" cy="12" rx="3" ry="2.4" stroke="currentColor" strokeWidth="1.75" />
      <ellipse cx="12" cy="12" rx="6" ry="4.8" stroke="currentColor" strokeWidth="1.5" />
      <ellipse cx="12" cy="12" rx="9.2" ry="7.4" stroke="currentColor" strokeWidth="1.5" />
    </Svg>
  );
}

export function IconHiddenLock(props: IconProps) {
  return (
    <Svg title={props.title ?? "Hidden to protect individuals"} {...props}>
      <rect height="9" rx="1.2" stroke="currentColor" strokeWidth="1.75" width="11" x="6.5" y="11" />
      <path d="M8.5 11 V8.4 A3.5 3.5 0 0 1 15.5 8.4 V11" stroke="currentColor" strokeWidth="1.75" />
    </Svg>
  );
}

export function IconEdgeQueue(props: IconProps) {
  return (
    <Svg title={props.title ?? "Queued on this phone"} {...props}>
      <path d="M4 7 H20" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <path d="M4 12 H16" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <path d="M4 17 H12" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <circle cx="19" cy="17" fill="currentColor" r="1.6" />
    </Svg>
  );
}

export function IconVaultKey(props: IconProps) {
  return (
    <Svg title={props.title ?? "Identity vault"} {...props}>
      <circle cx="9" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.75" />
      <path d="M12 12 H20 V15" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <path d="M17 12 V14.5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
    </Svg>
  );
}

export function IconBuddyPair(props: IconProps) {
  return (
    <Svg title={props.title ?? "Buddy"} {...props}>
      <circle cx="8" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.75" />
      <circle cx="16" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.75" />
      <path d="M4 18 C4 14.6 6 13 8 13 S12 14.6 12 18" stroke="currentColor" strokeWidth="1.75" />
      <path d="M12 18 C12 14.6 14 13 16 13 S20 14.6 20 18" stroke="currentColor" strokeWidth="1.75" />
    </Svg>
  );
}

export function IconLeaveWindow(props: IconProps) {
  return (
    <Svg title={props.title ?? "Leave window"} {...props}>
      <rect height="14" rx="2" stroke="currentColor" strokeWidth="1.75" width="16" x="4" y="6" />
      <path d="M4 10 H20" stroke="currentColor" strokeWidth="1.75" />
      <path d="M8 6 V4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <path d="M16 6 V4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
      <rect fill="currentColor" height="3.2" width="4.2" x="13" y="13" />
    </Svg>
  );
}

export function IconShiftMoon(props: IconProps) {
  return (
    <Svg title={props.title ?? "Night shift"} {...props}>
      <path
        d="M14 5.2 A7 7 0 1 0 18.8 15.5 A5.4 5.4 0 1 1 14 5.2 Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
    </Svg>
  );
}

export const CUSTOM_ICONS = {
  lay: IconLayRibbon,
  voice: IconVoiceContour,
  lock: IconHiddenLock,
  queue: IconEdgeQueue,
  vault: IconVaultKey,
  buddy: IconBuddyPair,
  leave: IconLeaveWindow,
  moon: IconShiftMoon,
} as const;
