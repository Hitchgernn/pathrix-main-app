import { useEffect, useRef, useState } from "react";
import { Command } from "cmdk";
import { Bookmark, Clock, Search, X } from "lucide-react";
import { useT } from "../../i18n";
import { searchPlaces } from "../../lib/api";
import { askFromAnywhere, goToPlace } from "../../lib/actions";
import type { Place } from "../../lib/places";
import { recentsForDisplay, useStore } from "../../store";
import { PlaceRow } from "../place/PlaceRow";

const DEBOUNCE_MS = 250;
const MIN_CHARS = 2;

type Status = "idle" | "loading" | "ready" | "failed";

interface SearchBarProps {
  /** `map` floats over the basemap; `page` sits inline on a screen. */
  variant: "map" | "page";
  className?: string;
}

/** The search bar and its results, as one anchored unit.
 *
 *  The results drop *beneath the bar the user is typing in* rather than taking
 *  over the screen, so the map never disappears and nothing navigates until a
 *  result is actually chosen. Both mount points (the map chrome and Beranda)
 *  render this same component, so there is exactly one search implementation.
 *
 *  Only one is ever mounted at a time — MapChrome renders on the Peta tab,
 *  HomeScreen on Beranda — so the query lives in local state. `searchOpen` is in
 *  the store because other chrome reacts to it: the filter chips step aside for
 *  the panel the way the reference does.
 */
export function SearchBar({ variant, className = "" }: SearchBarProps) {
  const open = useStore((s) => s.searchOpen);
  const setSearchOpen = useStore((s) => s.setSearchOpen);
  const savedPlaces = useStore((s) => s.savedPlaces);
  const recents = useStore((s) => s.recents);
  const t = useT();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const inputRef = useRef<HTMLInputElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);

  const close = () => {
    setSearchOpen(false);
    setQuery("");
    setResults([]);
    setStatus("idle");
    inputRef.current?.blur();
  };

  // Dismiss on Escape from anywhere, and on a click outside the whole unit —
  // the panel is anchored, not modal, so the rest of the app stays live.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_CHARS) {
      setResults([]);
      setStatus("idle");
      return;
    }
    setStatus("loading");
    let cancelled = false;
    const timer = window.setTimeout(() => {
      searchPlaces(trimmed)
        .then((hits) => {
          if (cancelled) return;
          setResults(hits);
          setStatus("ready");
        })
        .catch(() => {
          if (cancelled) return;
          setResults([]);
          setStatus("failed");
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  const choose = (place: Place) => {
    close();
    goToPlace(place);
  };

  const onMap = variant === "map";
  const typing = query.trim().length >= MIN_CHARS;
  const shortlist = recentsForDisplay(recents).slice(0, 4);

  return (
    <div ref={rootRef} className={`relative ${onMap ? "pointer-events-auto" : ""} ${className}`}>
      <Command
        // cmdk wires the input's aria-labelledby to this label, which wins over
        // a plain aria-label; without it the field has no accessible name.
        label={t("search.label")}
        shouldFilter={false}
        loop
        // Enter on the input with nothing highlighted should still do something
        // useful, so it falls through to the agent.
        onKeyDown={(event) => {
          if (event.key === "Enter" && !typing && query.trim()) {
            event.preventDefault();
            const text = query.trim();
            close();
            askFromAnywhere(text);
          }
        }}
      >
        <div
          className={`flex items-center gap-[10px] rounded-control px-[15px] focus-within:ring-2 focus-within:ring-ink ${
            onMap
              ? "surface-float py-[12px] shadow-float ring-1 ring-line"
              : "border border-line-strong bg-surface py-[13px]"
          }`}
        >
          <Search size={18} strokeWidth={1.9} className="flex-none text-ink-4" />
          <Command.Input
            ref={inputRef}
            value={query}
            onValueChange={setQuery}
            onFocus={() => setSearchOpen(true)}
            placeholder={t("search.placeholder")}
            className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-ink outline-none focus-visible:outline-none placeholder:text-ink-3"
          />
          {(query || open) && (
            <button
              onClick={close}
              aria-label={t("search.close")}
              className="flex-none text-ink-4 transition-colors hover:text-ink"
            >
              <X size={17} strokeWidth={2} />
            </button>
          )}
        </div>

        {open && (
          <Command.List
            className="absolute inset-x-0 top-[calc(100%+8px)] z-50 max-h-[min(60vh,420px)] animate-pxfade overflow-y-auto overscroll-contain rounded-card bg-surface p-2 shadow-float ring-1 ring-line"
          >
            {!typing ? (
              <>
                {savedPlaces.length > 0 && (
                  <Section icon={<Bookmark size={13} strokeWidth={2} />} label={t("search.saved")}>
                    {savedPlaces.slice(0, 3).map((place) => (
                      <Command.Item
                        key={place.id}
                        value={place.id}
                        onSelect={() => choose(place)}
                        className="rounded-[14px] data-[selected=true]:bg-surface-2"
                      >
                        <PlaceRow place={place} variant="compact" showFavourite={false} />
                      </Command.Item>
                    ))}
                  </Section>
                )}

                <Section icon={<Clock size={13} strokeWidth={2} />} label={t("search.recent")}>
                  {shortlist.map((entry) => (
                    <Command.Item
                      key={entry.prompt}
                      value={entry.prompt}
                      onSelect={() => {
                        close();
                        askFromAnywhere(entry.prompt);
                      }}
                      className="flex cursor-pointer items-center gap-3 rounded-[14px] px-2 py-[11px] data-[selected=true]:bg-surface-2"
                    >
                      <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-surface-3">
                        <Clock size={16} strokeWidth={1.8} className="text-ink-3" />
                      </span>
                      <span className="min-w-0 flex-1 truncate text-[15px]">{entry.title}</span>
                    </Command.Item>
                  ))}
                </Section>
              </>
            ) : status === "loading" ? (
              <p className="label-sm px-2 py-5 font-normal text-ink-3">{t("search.searching")}</p>
            ) : status === "failed" ? (
              <Note
                title={t("search.failedTitle")}
                body={t("search.failedBody")}
              />
            ) : results.length === 0 ? (
              <Note
                title={t("search.emptyTitle", query.trim())}
                body={t("search.emptyBody")}
                action={
                  <button
                    onClick={() => {
                      const text = query.trim();
                      close();
                      askFromAnywhere(text);
                    }}
                    className="mt-3 rounded-control bg-ink px-[16px] py-[10px] text-[14px] font-semibold text-surface transition-colors hover:bg-ink/90"
                  >
                    {t("search.askAgent")}
                  </button>
                }
              />
            ) : (
              <>
                {results.map((place) => (
                  <Command.Item
                    key={place.id}
                    value={place.id}
                    onSelect={() => choose(place)}
                    className="rounded-[14px] data-[selected=true]:bg-surface-2"
                  >
                    <PlaceRow
                      place={place}
                      variant="compact"
                      highlight={query.trim()}
                      showFavourite={false}
                    />
                  </Command.Item>
                ))}
                <p className="label-sm px-2 pb-1 pt-2 font-normal text-ink-3">
                  {t(
                    "search.results",
                    results.length,
                    results.some((r) => r.kind !== "address"),
                  )}
                </p>
              </>
            )}
          </Command.List>
        )}
      </Command>
    </div>
  );
}

function Section({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Command.Group className="pb-1">
      <div className="label-sm flex items-center gap-[7px] px-2 pb-1 pt-1 text-ink-3">
        <span className="text-ink-4">{icon}</span>
        {label}
      </div>
      {children}
    </Command.Group>
  );
}

function Note({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="px-2 py-4">
      <p className="title-row">{title}</p>
      <p className="body-13 mt-1 max-w-[42ch] text-ink-2">{body}</p>
      {action}
    </div>
  );
}
