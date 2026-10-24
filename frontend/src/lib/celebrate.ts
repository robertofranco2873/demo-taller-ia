import confetti from "canvas-confetti";

const COLORS = ["#c9a24d", "#e8a317", "#7c9cc9", "#9c8bc8", "#7a55e6", "#f5e9c8"];

function reduced() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/** Confeti al terminar una orden. */
export function celebrateOrder() {
  if (reduced()) return;
  confetti({ particleCount: 90, spread: 75, origin: { y: 0.7 }, colors: COLORS, disableForReducedMotion: true });
}

/** Lluvia más grande (con "globos" circulares) al alcanzar la meta de eficiencia. */
export function celebrateGoal() {
  if (reduced()) return;
  const end = Date.now() + 1200;
  const frame = () => {
    confetti({ particleCount: 5, angle: 60, spread: 60, origin: { x: 0, y: 0.8 }, colors: COLORS, shapes: ["circle"], scalar: 1.6 });
    confetti({ particleCount: 5, angle: 120, spread: 60, origin: { x: 1, y: 0.8 }, colors: COLORS, shapes: ["circle"], scalar: 1.6 });
    if (Date.now() < end) requestAnimationFrame(frame);
  };
  frame();
}
