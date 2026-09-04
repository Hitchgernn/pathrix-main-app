import { Bookmark, Building2, Home, MapPin, TramFront } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { KIND_META, type Place, type PlaceKind } from "../../lib/places";
import { FavouriteButton } from "./FavouriteButton";

const ICON: Record<PlaceKind, LucideIcon> = {
  poi: MapPin,
  properti: Building2,
  transit: TramFront,
  pangkalan: Bookmark,
  address: Home,
};

interface PlaceRowProps {
  place: Place;
  /** Search term to mark inside the name, so a hit shows why it matched. */
  highlight?: string;
  onClick?: () => void;
  showFavourite?: boolean;
  /** `compact` is the search result row: name and secondary text on one line,
   *  the way the reference sets it. `full` keeps two lines for saved lists. */
  variant?: "full" | "compact";
}

/** One result row, shared by search, saved, and the nearby strips. A hairline
 *  list, not a stack of cards — cards here would put a border around every
 *  single answer and make the list read as six competing objects. */
export function PlaceRow({
  place,
  highlight,
  onClick,
  showFavourite = true,
  variant = "full",
}: PlaceRowProps) {
  const Icon = ICON[place.kind];
  const meta = KIND_META[place.kind];

  const compact = variant === "compact";

  const body = compact ? (
    <>
      <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-surface-3">
        <Icon size={16} strokeWidth={1.8} className="text-ink-3" />
      </span>
      {/* One line, name then address, as the reference sets a result. The name
          is capped rather than allowed to consume the row, so a long name
          truncates but the address is still visible beside it. */}
      <span className="flex min-w-0 flex-1 items-baseline gap-[6px] text-[15px]">
        <span className="max-w-[62%] flex-none truncate font-semibold tracking-[-.01em]">
          {highlight ? <Marked text={place.name} term={highlight} /> : place.name}
        </span>
        {place.subtitle && (
          <span className="min-w-0 flex-1 truncate text-[13px] text-ink-3">{place.subtitle}</span>
        )}
      </span>
      {showFavourite && <FavouriteButton place={place} variant="chip" />}
    </>
  ) : (
    <>
      <span className="flex h-10 w-10 flex-none items-center justify-center rounded-[12px] bg-surface-2 ring-1 ring-line">
        <Icon size={18} strokeWidth={1.8} className={meta.className} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-semibold tracking-[-.01em]">
          {highlight ? <Marked text={place.name} term={highlight} /> : place.name}
        </span>
        <span className="mt-[2px] flex items-center gap-[6px]">
          <span className={`label-sm flex-none ${meta.className}`}>{meta.label}</span>
          {place.subtitle && (
            <span className="min-w-0 truncate text-[13px] text-ink-3">{place.subtitle}</span>
          )}
        </span>
      </span>
      {showFavourite && <FavouriteButton place={place} variant="chip" />}
    </>
  );

  if (!onClick) {
    return (
      <span
        className={`flex w-full cursor-pointer items-center gap-3 ${
          compact ? "px-2 py-[11px]" : "px-3 py-[11px]"
        }`}
      >
        {body}
      </span>
    );
  }
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-card px-3 py-[11px] text-left transition-colors hover:bg-surface-2"
    >
      {body}
    </button>
  );
}

/** Marks the matched substring so a result explains itself. Case-insensitive,
 *  first occurrence only — a name is short enough that one mark is the signal. */
function Marked({ text, term }: { text: string; term: string }) {
  const index = text.toLowerCase().indexOf(term.toLowerCase());
  if (index < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, index)}
      <mark className="bg-transparent font-semibold text-ink">
        {text.slice(index, index + term.length)}
      </mark>
      {text.slice(index + term.length)}
    </>
  );
}
