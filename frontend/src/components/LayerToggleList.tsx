import { LAYER_ROWS } from "../lib/sample";
import { useStore } from "../store";
import { Switch } from "./ui/switch";

/** Layer catalogue. Data is fetched when a layer is switched on, not all at
 *  boot — that is most of the load budget (ARCHITECTURE.md §14). */
export function LayerToggleList() {
  const active = useStore((s) => s.active);
  const catalogue = useStore((s) => s.catalogue);
  const toggleLayer = useStore((s) => s.toggleLayer);

  const servedBy = new Set(catalogue.map((entry) => entry.id));

  return (
    <div>
      <div className="body-13 mb-[14px] max-w-[48ch] text-ink-2">
        Data dimuat saat layer diaktifkan, bukan sekaligus di awal.
      </div>

      {LAYER_ROWS.map((row) => {
        const on = active.has(row.id);
        // A row the backend catalogue does not serve yet is still shown — the
        // design is the visual contract — but its meta line says so.
        const live = row.backendId !== null && servedBy.has(row.backendId);
        return (
          <div key={row.id} className="hairline flex items-center gap-[13px] py-[15px]">
            <span
              className="h-[14px] w-[14px] flex-none rounded-[3px] border"
              style={{
                background: row.color,
                borderColor: row.id === "bangunan" ? "rgba(16,30,42,.3)" : "transparent",
              }}
            />
            <div className="min-w-0 flex-1">
              <div className="title-row">{row.name}</div>
              <div className="body-13 mt-[3px] text-ink-3">
                {live || catalogue.length === 0 ? row.meta : `${row.meta}, belum tersambung`}
              </div>
            </div>
            <Switch
              checked={on}
              onCheckedChange={() => toggleLayer(row.id)}
              aria-label={row.name}
            />
          </div>
        );
      })}
      <div className="hairline" />
    </div>
  );
}
