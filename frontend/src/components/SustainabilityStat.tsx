import { kg } from "../lib/format";
import { SAMPLE_CARBON } from "../lib/sample";
import { useStore } from "../store";

/** Carbon saved, with its basis and citation on the same screen. The number is
 *  never shown without the source — that traceability is a scored deliverable
 *  (ARCHITECTURE.md §5.1, emission_factors carries its own citation). */
export function SustainabilityStat() {
  const openPanel = useStore((s) => s.openPanel);
  const carbon = useStore((s) => s.lastCarbon);
  const messages = useStore((s) => s.messages);
  // The empty state is a real state now, not a prototype switch: nothing has
  // been calculated yet this session, so there is no figure to show.
  const empty = carbon === null && messages.length === 0;

  return (
    <div>
      {!empty ? (
        <div>
          <div className="figure font-medium leading-none tracking-[-.03em] text-gold-text text-[clamp(38px,7vw,58px)]">
            {carbon ? kg(carbon.saved_g_co2) : SAMPLE_CARBON.trip}
          </div>
          <div className="label-sm mt-[10px] text-ink-3">CO₂e terhindari, perjalanan ini</div>
          <div className="body-13 mt-3 max-w-[52ch] text-ink-2">{SAMPLE_CARBON.basis}</div>
          <div className="body-13 mt-[10px] text-ink-3">
            {carbon ? `Sumber: ${carbon.source_citation}` : `Sumber: ${SAMPLE_CARBON.source}`}
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
              <span className="figure flex-none whitespace-nowrap text-[16px] font-medium text-gold-text">
                {SAMPLE_CARBON.month}
              </span>
            </div>
            <div className="hairline flex items-baseline justify-between gap-3 py-[14px]">
              <span className="title-row min-w-0 flex-1 whitespace-nowrap">Perjalanan tercatat</span>
              <span className="figure flex-none whitespace-nowrap text-[13px] text-ink-2">
                {SAMPLE_CARBON.trips}
              </span>
            </div>
            <div className="hairline" />
          </div>
        </div>
      ) : (
        <div>
          <div className="label-sm text-ink-3">Belum ada perjalanan tercatat</div>
          <div className="body-15 mt-3 max-w-[46ch] text-ink-2">
            Belum ada perjalanan tercatat. Hitung satu rute dan angkanya muncul di sini bersama
            sumbernya.
          </div>
          <div className="body-13 mt-[18px] text-ink-3">
            Faktor emisi siap: KLHK (2023), IPCC 2006 Tier 1.
          </div>
          <button
            onClick={() => openPanel("route")}
            className="mt-5 rounded-control bg-ink px-5 py-[13px] text-[15px] font-semibold text-surface transition-colors hover:bg-ink/90"
          >
            Lihat rute contoh
          </button>
        </div>
      )}
    </div>
  );
}
