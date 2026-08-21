import { kg } from "../lib/format";
import { SAMPLE_CARBON } from "../lib/sample";
import { useStore } from "../store";

/** Carbon saved, with its basis and citation on the same screen. The number is
 *  never shown without the source — that traceability is a scored deliverable
 *  (ARCHITECTURE.md §5.1, emission_factors carries its own citation). */
export function SustainabilityStat() {
  const empty = useStore((s) => s.sustainEmpty);
  const setEmpty = useStore((s) => s.setSustainEmpty);
  const openPanel = useStore((s) => s.openPanel);
  const carbon = useStore((s) => s.lastCarbon);

  return (
    <div>
      {!empty ? (
        <div>
          <div className="font-semibold leading-none tracking-[-.03em] text-gold text-[clamp(38px,7vw,58px)]">
            {carbon ? kg(carbon.saved_g_co2) : SAMPLE_CARBON.trip}
          </div>
          <div className="kicker mt-[10px] text-ink-55">CO₂E TERHINDARI · PERJALANAN INI</div>
          <div className="body-13 mt-3 max-w-[52ch] text-ink-66">{SAMPLE_CARBON.basis}</div>
          <div className="kicker mt-[10px] leading-[1.7] text-ink-50">
            {carbon ? `SOURCE · ${carbon.source_citation.toUpperCase()}` : SAMPLE_CARBON.source}
            {!carbon && (
              <>
                <br />
                {SAMPLE_CARBON.caveat}
              </>
            )}
          </div>

          <div className="mt-[22px]">
            <div className="hairline flex items-baseline justify-between gap-3 py-[14px]">
              <span className="title-row min-w-0 flex-1 whitespace-nowrap">Bulan ini</span>
              <span className="flex-none whitespace-nowrap text-[16px] font-semibold text-gold">
                {SAMPLE_CARBON.month}
              </span>
            </div>
            <div className="hairline flex items-baseline justify-between gap-3 py-[14px]">
              <span className="title-row min-w-0 flex-1 whitespace-nowrap">Perjalanan tercatat</span>
              <span className="kicker flex-none whitespace-nowrap text-ink-55">
                {SAMPLE_CARBON.trips}
              </span>
            </div>
            <div className="hairline" />
          </div>
        </div>
      ) : (
        <div>
          <div className="kicker text-ink-45">NO TRIPS RECORDED</div>
          <div className="body-15 mt-3 max-w-[46ch] text-ink-72">
            Belum ada perjalanan tercatat. Hitung satu rute dan angkanya muncul di sini bersama
            sumbernya.
          </div>
          <div className="kicker mt-[18px] leading-[1.7] text-ink-50">
            FACTORS READY · KLHK (2023) · IPCC 2006 TIER 1
          </div>
          <button
            onClick={() => openPanel("route")}
            className="mt-5 rounded-full bg-blue px-5 py-[13px] text-[15px] font-semibold text-surface transition-colors hover:bg-ink"
          >
            Lihat rute contoh
          </button>
        </div>
      )}

      <button onClick={() => setEmpty(!empty)} className="kicker mt-[22px] text-ink-40">
        {empty ? "SHOW RECORDED STATE" : "SHOW EMPTY STATE"}
      </button>
    </div>
  );
}
