import { ArrowLeft, MessageCircle, Navigation, Share2, Star } from "lucide-react";
import { askFromAnywhere } from "../../lib/actions";
import { KIND_META } from "../../lib/places";
import { NAV_W, NAV_W_COLLAPSED, TABBAR_H } from "../../lib/tokens";
import { usePhoto } from "../../lib/usePhoto";
import { useStore } from "../../store";
import { PhotoSlot } from "../PhotoSlot";
import { FavouriteButton } from "./FavouriteButton";

/** The detail surface for a tapped marker or a chosen search result, following
 *  inspirations/pathrix-inspiration-halte-or-place.png: circular back, centred
 *  title, heart; hero photograph with a glass circular action; a status pill
 *  row; title; outlined fact chips; detail rows; and a sticky footer of one
 *  quiet action beside one filled one.
 *
 *  On mobile it rises from the bottom over the map. On desktop it is the same
 *  card, anchored beside the nav next to the pin the map just flew to.
 */
export function PlaceSheet() {
  const place = useStore((s) => s.selectedPlace);
  const selectPlace = useStore((s) => s.selectPlace);
  const wide = useStore((s) => s.wide);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const { photo, resolved } = usePhoto(place?.name);

  if (!place) return null;

  const meta = KIND_META[place.kind];
  const coords = `${place.coord[1].toFixed(5)}, ${place.coord[0].toFixed(5)}`;
  const hero = place.photoUrl ?? photo?.url ?? null;

  const source =
    place.kind === "address"
      ? "Nominatim MAPID"
      : place.kind === "pangkalan"
        ? "Survei lapangan"
        : place.kind === "transit"
          ? "Data transit Pathrix"
          : "Misi MAPID Apps";

  const position = wide
    ? {
        left: (navCollapsed ? NAV_W_COLLAPSED : NAV_W) + 20,
        top: 128,
        width: 372,
        maxHeight: "calc(100% - 176px)",
      }
    : {
        left: 12,
        right: 12,
        bottom: `calc(env(safe-area-inset-bottom, 0px) + ${TABBAR_H + 22}px)`,
        maxHeight: "78%",
      };

  return (
    <section
      aria-label={place.name}
      className="absolute z-[60] flex animate-pxrise flex-col overflow-hidden rounded-sheet bg-surface shadow-float ring-1 ring-line"
      style={position}
    >
      <header className="flex flex-none items-center gap-2 px-3 pb-2 pt-3">
        <button
          onClick={() => selectPlace(null)}
          aria-label="Tutup"
          className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-surface-3 transition-colors hover:bg-line-strong"
        >
          <ArrowLeft size={19} strokeWidth={1.9} />
        </button>
        <h2 className="title-row min-w-0 flex-1 truncate text-center">Detail tempat</h2>
        <FavouriteButton place={place} />
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <div className="relative">
          <div className="h-[168px] w-full overflow-hidden rounded-card">
            <PhotoSlot
              src={hero}
              alt={place.name}
              placeholder="Foto survei belum tersedia untuk titik ini"
              radius={20}
              pending={!resolved}
            />
          </div>

          {hero && (
            <button
              onClick={() => askFromAnywhere(`Ceritakan tentang ${place.name}`)}
              aria-label="Tanya agen tentang tempat ini"
              className="surface-float absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full shadow-card"
            >
              <MessageCircle size={16} strokeWidth={1.9} />
            </button>
          )}
        </div>

        {/* The reference pairs a status pill with a rating pill under the hero.
            Ours carry the two things we can stand behind: what kind of place
            this is, and whether a surveyor actually stood there. */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="label-sm rounded-control bg-surface-3 px-[11px] py-[6px] text-ink-2">
            {meta.label}
          </span>
          {place.kind === "pangkalan" && (
            <span className="label-sm flex items-center gap-[5px] rounded-control bg-surface px-[11px] py-[6px] text-gold-text ring-1 ring-line">
              <Star size={13} strokeWidth={0} fill="var(--color-gold)" aria-hidden />
              Survei lapangan
            </span>
          )}
        </div>

        <h3 className="title-lg mt-3">{place.name}</h3>
        {place.subtitle && <p className="body-13 mt-[6px] text-ink-2">{place.subtitle}</p>}

        {place.facts.length > 0 && (
          <div className="mt-[14px] flex flex-wrap gap-[6px]">
            {place.facts.map((fact) => (
              <span
                key={fact.label}
                className="rounded-control border border-line-strong px-[12px] py-[7px] text-[13px] text-ink-2"
              >
                {fact.label}: <span className="figure text-ink">{fact.value}</span>
              </span>
            ))}
          </div>
        )}

        <h4 className="label-sm mt-[22px]">Detail</h4>
        <dl className="mt-1">
          <Row label="Koordinat" value={coords} mono />
          <Row label="Sumber" value={source} />
          {photo && !place.photoUrl && <Row label="Foto" value={photo.credit} href={photo.href} />}
        </dl>

        {place.facts.length === 0 && place.kind !== "address" && (
          <p className="body-13 mt-[14px] text-ink-3">
            Jam operasional dan tarif akan muncul di sini setelah digitalisasi survei lapangan
            selesai.
          </p>
        )}
      </div>

      <div className="flex flex-none items-center gap-[10px] border-t border-line px-3 pb-[16px] pt-[14px]">
        <button
          onClick={() => {
            const text = `${place.name}, ${coords}`;
            if (navigator.share) void navigator.share({ title: place.name, text }).catch(() => {});
            else void navigator.clipboard?.writeText(text).catch(() => {});
          }}
          aria-label="Bagikan lokasi"
          className="flex h-[50px] w-[50px] flex-none items-center justify-center rounded-control border border-line-strong text-ink-2 transition-colors hover:bg-surface-2"
        >
          <Share2 size={17} strokeWidth={1.9} />
        </button>
        <button
          onClick={() => askFromAnywhere(`Rute ke ${place.name}`)}
          className="flex h-[50px] flex-1 items-center justify-center gap-[9px] rounded-control bg-ink text-[15px] font-semibold tracking-[-.01em] text-surface transition-[background-color,transform] hover:bg-ink/90 active:scale-[.985]"
        >
          <Navigation size={17} strokeWidth={2} />
          Rute ke sini
        </button>
      </div>
    </section>
  );
}

function Row({
  label,
  value,
  mono,
  href,
}: {
  label: string;
  value: string;
  mono?: boolean;
  href?: string;
}) {
  return (
    <div className="hairline flex items-baseline justify-between gap-4 py-[11px]">
      <dt className="label-sm flex-none font-normal text-ink-3">{label}</dt>
      <dd className={`min-w-0 truncate text-right text-[13px] text-ink-2 ${mono ? "figure" : ""}`}>
        {href ? (
          <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
            {value}
          </a>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}
