import { QUICK, RECENT, SAMPLE_CARBON } from "../lib/sample";
import { useStore } from "../store";

/** Entry screen. The map deliberately loads after this — the PRD asks for a
 *  dashboard before the map, and it keeps MapLibre out of the first paint
 *  (ARCHITECTURE.md §14). */
export function Dashboard() {
  const input = useStore((s) => s.input);
  const setInput = useStore((s) => s.setInput);
  const setScreen = useStore((s) => s.setScreen);
  const ask = useStore((s) => s.ask);
  const openPanel = useStore((s) => s.openPanel);

  const enterApp = (prompt?: string) => {
    setScreen("app");
    if (prompt) ask(prompt);
  };

  return (
    <div className="absolute inset-0 bg-ground flex flex-col px-4 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[560px] min-h-full flex-col pt-7 pb-6">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[19px] font-bold tracking-[.10em]">PATHRIX</span>
          <span className="kicker text-ink-55">YOGYAKARTA · MULTIMODA</span>
        </div>

        <div className="mt-[18px] h-px bg-line" />

        <h1 className="title-lg mt-[34px] max-w-[15ch]">Mau ke mana hari ini?</h1>
        <p className="body-15 mt-[10px] max-w-[44ch] text-ink-66">
          Tanya rute, halte, atau tempat. Agen menyusun perjalanan lintas moda — bus, KRL,
          kereta bandara, andong dan becak.
        </p>

        <div className="mt-[26px] flex items-center gap-[10px] rounded-full border border-line bg-surface px-[18px] py-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              enterApp(input || "Malioboro → Candi Prambanan");
            }}
            placeholder="Tujuan, atau tanya agen…"
            className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-ink outline-none"
          />
          <button onClick={() => enterApp(input || undefined)} className="kicker text-blue">
            GO
          </button>
        </div>

        <div className="mt-[14px] flex flex-wrap gap-2">
          {QUICK.map((q) => (
            <button
              key={q.text}
              onClick={() => enterApp(q.text)}
              className="body-13 flex-none whitespace-nowrap rounded-full border border-line bg-surface-2 px-[15px] py-2 text-ink transition-colors hover:border-blue hover:bg-blue hover:text-surface"
            >
              {q.text}
            </button>
          ))}
        </div>

        <div className="mt-9">
          <div className="kicker text-ink-55">RECENT</div>
          <div className="mt-3">
            {RECENT.map((r) => (
              <button
                key={r.title}
                onClick={() => enterApp(r.prompt)}
                className="hairline flex w-full items-baseline justify-between gap-3 px-[2px] py-[13px] text-left hover:bg-surface-2"
              >
                <span className="title-row min-w-0 flex-1 truncate">{r.title}</span>
                <span className="kicker whitespace-nowrap text-ink-50">{r.meta}</span>
              </button>
            ))}
            <div className="hairline" />
          </div>
        </div>

        <button
          onClick={() => {
            setScreen("app");
            openPanel("sustain");
          }}
          className="mt-[30px] flex items-baseline gap-3 text-left"
        >
          <span className="text-[32px] font-semibold tracking-[-.02em] text-gold">
            {SAMPLE_CARBON.month}
          </span>
          <span className="flex flex-col gap-[3px]">
            <span className="kicker text-ink-55">CO₂E TERHINDARI · BULAN INI</span>
            <span className="body-13 text-ink-66">Dasar perhitungan &amp; sumber →</span>
          </span>
        </button>

        <div className="min-h-[26px] flex-1" />

        <button
          onClick={() => enterApp()}
          className="mt-5 w-full rounded-full bg-blue px-[22px] py-4 text-[16px] font-semibold tracking-[-.01em] text-surface transition-colors hover:bg-ink"
        >
          Buka peta
        </button>
        <div className="kicker mt-[14px] text-center text-ink-40">MAP LOADS AFTER THIS SCREEN</div>
      </div>
    </div>
  );
}
