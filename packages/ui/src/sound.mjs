export function soundEnabled() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem("manobal.sound") === "on";
}

export function setSoundEnabled(on) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("manobal.sound", on ? "on" : "off");
}

export function hapticsEnabled() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.localStorage.getItem("manobal.haptics") !== "off";
}

export function vibrate(pattern) {
  if (typeof navigator === "undefined" || !hapticsEnabled()) {
    return;
  }
  if (typeof navigator.vibrate !== "function") {
    return;
  }
  navigator.vibrate(pattern);
}

export function tickCheckIn() {
  vibrate(8);
}

export function tickComplete() {
  vibrate([8, 40, 8]);
}

export function breathPulse() {
  vibrate([12, 80, 12]);
}

function tone(frequency, duration, when = 0, force = false) {
  if (typeof window === "undefined" || (!force && !soundEnabled())) {
    return;
  }
  const Ctor = window.AudioContext;
  if (!Ctor) {
    return;
  }
  const ctx = new Ctor();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequency;
  gain.gain.value = 0.04;
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(ctx.currentTime + when);
  oscillator.stop(ctx.currentTime + when + duration);
}

export function chimeT3() {
  tone(440, 0.12);
  tone(554, 0.14, 0.12);
}

export function chimeT4() {
  tone(392, 0.1);
  tone(494, 0.1, 0.12);
  tone(587, 0.16, 0.24);
}

export function chimeKindForQueue(t4Count, t3Count) {
  if (t4Count > 0) {
    return "t4";
  }
  if (t3Count > 0) {
    return "t3";
  }
  return "";
}

export function playConsoleChime(kind) {
  if (kind === "t4") {
    tone(392, 0.1, 0, true);
    tone(494, 0.1, 0.12, true);
    tone(587, 0.16, 0.24, true);
    return;
  }
  if (kind === "t3") {
    tone(440, 0.12, 0, true);
    tone(554, 0.14, 0.12, true);
  }
}
