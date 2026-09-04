import { ArrowRight, ChevronRight, Layers, Leaf, Route, TramFront } from "lucide-react";
import type { ComponentType } from "react";
import { askFromAnywhere, goToPlace } from "../../lib/actions";
import { QUICK_ACTIONS, SAMPLE_CARBON, type QuickAction } from "../../lib/sample";
import { usePhoto } from "../../lib/usePhoto";
import { recentsForDisplay, useStore } from "../../store";
import { Avatar } from "../ui/avatar";
import { Carriage, type GlyphProps } from "../icons";
import { SearchBar } from "../search/SearchPanel";

const TILE_ICON: Record<QuickAction["icon"], ComponentType<GlyphProps>> = {
  route: Route,
  bus: TramFront,
  carriage: Carriage,
  layers: Layers,
};

/** The entry screen, composed like inspirations/pathrix-inspiration-ui-mobile-main.png:
 *  avatar and a single status chip on one line, a light large greeting, a wide
 *  action card, then photo-led tiles and the recent list.
 *
 *  MapLibre is still not loaded at this point (ARCHITECTURE.md §14). */
export function HomeScreen() {
  const profile = useStore((s) => s.profile);
  const savedPlaces = useStore((s) => s.savedPlaces);
  const recents = useStore((s) => s.recents);
  const setTab = useStore((s) => s.setTab);
  const openPanel = useStore((s) => s.openPanel);
  const toggleLayer = useStore((s) => s.toggleLayer);

  const runAction = (action: QuickAction) => {
    if (action.layers) action.layers.forEach((id) => toggleLayer(id, true));
    if (action.prompt) {
      askFromAnywhere(action.prompt);
      return;
    }
    setTab("explore");
    if (action.id === "layer") openPanel("layers");
  };

  return (
    <div className="mx-auto flex w-full max-w-[600px] flex-col px-4 pb-16 pt-6">
      <header className="flex items-center gap-3">
        <Avatar src={profile.avatar} name={profile.name} className="h-11 w-11" />
        <div className="min-w-0 flex-1" />
        <button
          onClick={() => {
            setTab("explore");
            openPanel("sustain");
          }}
          className="flex flex-none items-center gap-[9px] rounded-control bg-gold-tint px-[13px] py-[9px] text-left transition-transform active:scale-[.98]"
        >
          <Leaf size={17} strokeWidth={1.9} className="text-gold-text" />
          <span>
            <span className="figure block text-[14px] font-medium leading-none text-gold-text">
              {SAMPLE_CARBON.month}
            </span>
            <span className="label-sm mt-[4px] block font-normal leading-none text-gold-text">
              CO₂e bulan ini
            </span>
          </span>
        </button>
      </header>

      <h1 className="title-greeting mt-7">
        Halo, {profile.name}
        <br />
        <span className="font-medium">Mau ke mana hari ini?</span>
      </h1>

      <SearchBar variant="page" className="mt-6" />

      {/* The reference's wide "Book a ride" card: one filled action against a
          quiet surface, with the useful figure sitting beside it. */}
      <button
        onClick={() => setTab("explore")}
        className="group mt-[10px] flex items-center gap-3 rounded-tile bg-surface p-[14px] text-left ring-1 ring-line transition-shadow hover:shadow-card"
      >
        <span className="flex h-[46px] flex-1 items-center justify-center rounded-control bg-ink px-5 text-[15px] font-semibold text-surface transition-transform group-active:scale-[.985]">
          Buka peta
        </span>
        <span className="flex flex-none items-center gap-[6px] pr-2 text-ink-2">
          <span className="figure text-[13px]">{savedPlaces.length}</span>
          <span className="label-sm font-normal text-ink-3">tersimpan</span>
          <ArrowRight size={15} strokeWidth={2} className="text-ink-4" />
        </span>
      </button>

      <div className="mt-[10px] grid auto-rows-fr grid-cols-2 gap-[10px]">
        {QUICK_ACTIONS.map((action) => (
          <ActionTile key={action.id} action={action} onSelect={() => runAction(action)} />
        ))}
      </div>

      {savedPlaces.length > 0 && (
        <section className="mt-9">
          <SectionHead label="Tersimpan" onMore={() => setTab("saved")} />
          <div className="no-scrollbar -mx-4 mt-3 flex gap-[10px] overflow-x-auto px-4 pb-1">
            {savedPlaces.slice(0, 6).map((place) => (
              <button
                key={place.id}
                onClick={() => goToPlace(place)}
                className="w-[172px] flex-none rounded-card bg-surface p-[13px] text-left ring-1 ring-line transition-shadow hover:shadow-card"
              >
                <span className="block truncate text-[14px] font-semibold tracking-[-.01em]">
                  {place.name}
                </span>
                <span className="mt-[3px] block truncate text-[12.5px] text-ink-3">
                  {place.subtitle ?? "Tersimpan di perangkat ini"}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="mt-9">
        <SectionHead label={recents.length > 0 ? "Terakhir" : "Contoh perjalanan"} />
        <div className="mt-2">
          {recentsForDisplay(recents)
            .slice(0, 5)
            .map((entry) => (
              <button
                key={entry.prompt}
                onClick={() => askFromAnywhere(entry.prompt)}
                className="hairline flex w-full items-center gap-3 py-[14px] text-left transition-colors hover:bg-surface-2"
              >
                <span className="min-w-0 flex-1 truncate text-[15px] font-medium tracking-[-.01em]">
                  {entry.title}
                </span>
                <span className="figure flex-none whitespace-nowrap text-[12px] text-ink-3">
                  {relativeDay(entry.at)}
                </span>
                <ChevronRight size={16} strokeWidth={2} className="flex-none text-ink-4" />
              </button>
            ))}
          <div className="hairline" />
        </div>
        {recents.length === 0 && (
          <p className="body-13 mt-3 text-ink-3">
            Contoh perjalanan. Riwayat asli Anda muncul di sini setelah pencarian pertama.
          </p>
        )}
      </section>
    </div>
  );
}

/** A photo-led tile, like the reference's Find Ride / Flight Book / Parcel /
 *  Food grid. The photograph is real (Wikimedia) where one honestly exists for
 *  the subject; the layer tile has no photographable subject and stays
 *  iconographic rather than borrowing an unrelated image. */
function ActionTile({ action, onSelect }: { action: QuickAction; onSelect: () => void }) {
  const Icon = TILE_ICON[action.icon];
  const { photo } = usePhoto(action.photo ?? null);

  return (
    <button
      onClick={onSelect}
      className="group flex h-full flex-col overflow-hidden rounded-tile bg-surface text-left ring-1 ring-line transition-[box-shadow,transform] hover:shadow-card active:scale-[.985]"
    >
      <span className="relative block h-[92px] w-full overflow-hidden bg-surface-3">
        {photo ? (
          <img
            src={photo.url}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:scale-[1.04]"
          />
        ) : (
          <span className="flex h-full w-full items-center justify-center">
            <Icon size={26} strokeWidth={1.5} className="text-ink-4" />
          </span>
        )}
      </span>
      <span className="block flex-1 px-[14px] pb-[14px] pt-[11px]">
        <span className="block text-[15px] font-semibold tracking-[-.01em]">{action.title}</span>
        <span className="mt-[2px] block text-[12.5px] leading-[1.35] text-ink-3">{action.sub}</span>
      </span>
    </button>
  );
}

function SectionHead({ label, onMore }: { label: string; onMore?: () => void }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <h2 className="title-row">{label}</h2>
      {onMore && (
        <button onClick={onMore} className="text-[13px] font-semibold text-ink-2 hover:text-ink">
          Lihat semua
        </button>
      )}
    </div>
  );
}

/** Indonesian relative day. Anything past a fortnight becomes a date, because
 *  "37 hari lalu" is not how anyone reads a list. */
function relativeDay(at: number): string {
  const days = Math.floor((Date.now() - at) / 864e5);
  if (days <= 0) return "Hari ini";
  if (days === 1) return "Kemarin";
  if (days < 14) return `${days} hari lalu`;
  return new Date(at).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}
