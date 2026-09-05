import { Heart } from "lucide-react";
import { useT } from "../../i18n";
import type { Place } from "../../lib/places";
import { useStore } from "../../store";

interface FavouriteButtonProps {
  place: Place;
  /** `bare` sits on a photo or a sheet header; `chip` sits inside a list row. */
  variant?: "bare" | "chip";
}

/** Saving is local to this device — there is no account behind it — so the
 *  control says "Simpan", never "Favoritkan ke akun Anda". */
export function FavouriteButton({ place, variant = "bare" }: FavouriteButtonProps) {
  const saved = useStore((s) => s.savedPlaces.some((p) => p.id === place.id));
  const toggle = useStore((s) => s.toggleSavedPlace);
  const t = useT();

  return (
    <button
      onClick={(event) => {
        event.stopPropagation();
        toggle(place);
      }}
      aria-pressed={saved}
      aria-label={t(saved ? "place.unsave" : "place.save", place.name)}
      className={
        variant === "chip"
          ? "flex-none rounded-full p-2 transition-colors hover:bg-surface-3"
          : "surface-float flex h-10 w-10 flex-none items-center justify-center rounded-full shadow-card ring-1 ring-line transition-transform active:scale-95"
      }
    >
      <Heart
        size={variant === "chip" ? 17 : 19}
        strokeWidth={1.9}
        className={saved ? "text-ink" : "text-ink-4"}
        fill={saved ? "currentColor" : "none"}
      />
    </button>
  );
}
