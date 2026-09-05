import { ChevronRight, Layers, Leaf, Route, TramFront } from "lucide-react";
import type { ComponentType } from "react";
import { currentLocale, useT } from "../../i18n";
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
  const t = useT();

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
              {t("home.carbonMonth")}
            </span>
          </span>
        </button>
      </header>

      <h1 className="title-greeting mt-7">
        {t("home.greeting", profile.name)}
        <br />
        <span className="font-medium">{t("home.question")}</span>
      </h1>

      <SearchBar variant="page" className="mt-6" />

      <div className="mt-3 grid auto-rows-fr grid-cols-2 gap-[10px]">
        {QUICK_ACTIONS.map((action) => (
          <ActionTile key={action.id} action={action} onSelect={() => runAction(action)} />
        ))}
      </div>

      {savedPlaces.length > 0 && (
        <section className="mt-9">
          <SectionHead label={t("search.saved")} onMore={() => setTab("saved")} />
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
                  {place.subtitle ?? t("home.savedOnDevice")}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="mt-9">
        <SectionHead label={t(recents.length > 0 ? "home.recent" : "home.sampleTrips")} />
        <div className="mt-2">
          {recentsForDisplay(recents, t)
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
                  {relativeDay(entry.at, t)}
                </span>
                <ChevronRight size={16} strokeWidth={2} className="flex-none text-ink-4" />
              </button>
            ))}
          <div className="hairline" />
        </div>
        {recents.length === 0 && (
          <p className="body-13 mt-3 text-ink-3">
            {t("home.sampleNote")}
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
  const t = useT();
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
        <span className="block text-[15px] font-semibold tracking-[-.01em]">
          {t(action.titleKey)}
        </span>
        <span className="mt-[2px] block text-[12.5px] leading-[1.35] text-ink-3">
          {t(action.subKey)}
        </span>
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

/** Relative day. Anything past a fortnight becomes a date, because "37 days
 *  ago" is not how anyone reads a list. */
function relativeDay(at: number, t: ReturnType<typeof useT>): string {
  const days = Math.floor((Date.now() - at) / 864e5);
  if (days <= 0) return t("time.today");
  if (days === 1) return t("time.yesterday");
  if (days < 14) return t("time.daysAgo", days);
  return new Date(at).toLocaleDateString(currentLocale() === "en" ? "en-GB" : "id-ID", {
    day: "numeric",
    month: "short",
  });
}
