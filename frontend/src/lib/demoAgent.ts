/** The scripted agent, for the window before an LLM provider is wired.
 *
 *  `app/agent/llm.py` deliberately has no provider chosen yet, so `/ws` answers
 *  `llm_unavailable` and the client falls back to here. A flat pause followed by
 *  one canned paragraph read as a stub; walking the steps a real answer would
 *  take reads as the product, and costs nothing in honesty as long as the sheet
 *  keeps saying it is a simulation — which it does, in the header, permanently.
 *
 *  The steps are not decoration. Each one names a thing the real agent will
 *  actually do: read the viewport, resolve the endpoints against the graph,
 *  run the weighted shortest path, price the carbon. When the provider lands,
 *  these become progress the backend reports rather than lines a timer prints.
 */

export type DemoKind = "route" | "nearby" | "generic";

export interface DemoStep {
  /** Shown while this step is the current one. */
  label: string;
  /** How long it holds before the next step takes over. */
  ms: number;
}

/** Which script a question gets. Cheap heuristics on purpose: the point is that
 *  a route question walks route steps, not that the classifier is clever. */
export function demoKindFor(text: string): DemoKind {
  const q = text.toLowerCase();
  if (/→|->|\bke\b|\bdari\b|rute|route|menuju/.test(q)) return "route";
  if (/terdekat|sekitar|dekat|nearby|near me|around/.test(q)) return "nearby";
  return "generic";
}

const SCRIPTS: Record<DemoKind, DemoStep[]> = {
  route: [
    { label: "Membaca peta yang Anda lihat", ms: 700 },
    { label: "Mencari titik awal dan tujuan", ms: 900 },
    { label: "Menyusun rute lintas moda", ms: 1100 },
    { label: "Menghitung tarif dan jejak karbon", ms: 800 },
  ],
  nearby: [
    { label: "Membaca peta yang Anda lihat", ms: 700 },
    { label: "Mencari halte dan pangkalan di sekitar", ms: 1000 },
  ],
  generic: [
    { label: "Membaca peta yang Anda lihat", ms: 700 },
    { label: "Menyiapkan jawaban", ms: 800 },
  ],
};

export const scriptFor = (kind: DemoKind): DemoStep[] => SCRIPTS[kind];

export const scriptDuration = (kind: DemoKind): number =>
  SCRIPTS[kind].reduce((total, step) => total + step.ms, 0);

/** Walks a script, reporting the index of the step currently running, then
 *  calls `done`. Returns a canceller — a second question must abandon the first
 *  script rather than interleaving two sets of steps into one conversation. */
export function runScript(
  kind: DemoKind,
  onStep: (index: number) => void,
  done: () => void,
): () => void {
  const steps = SCRIPTS[kind];
  let cancelled = false;
  let timer: number | null = null;

  const advance = (index: number) => {
    if (cancelled) return;
    if (index >= steps.length) {
      done();
      return;
    }
    onStep(index);
    timer = window.setTimeout(() => advance(index + 1), steps[index].ms);
  };

  advance(0);

  return () => {
    cancelled = true;
    if (timer !== null) window.clearTimeout(timer);
  };
}
