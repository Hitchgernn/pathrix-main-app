import { useEffect, useRef, useState } from "react";
import { Command } from "cmdk";
import { ArrowLeft, Bookmark, Clock, Search, X } from "lucide-react";
import { searchPlaces } from "../../lib/api";
import { askFromAnywhere, goToPlace } from "../../lib/actions";
import type { Place } from "../../lib/places";
import { useStore, recentsForDisplay } from "../../store";
import { PlaceRow } from "../place/PlaceRow";

const DEBOUNCE_MS = 250;
const MIN_CHARS = 2;

type Status = "idle" | "loading" | "ready" | "failed";

/** One search surface for the whole app.
 *
 *  cmdk supplies the listbox semantics and arrow-key movement; the filtering is
 *  ours and server-side (`shouldFilter={false}`), because the corpus is the
 *  backend's mirrored rows plus geocoded addresses, not a list already in the
 *  client.
 */
export function SearchOverlay() {
  const open = useStore((s) => s.searchOpen);
  const setSearchOpen = useStore((s) => s.setSearchOpen);
  const savedPlaces = useStore((s) => s.savedPlaces);
  const recents = useStore((s) => s.recents);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setResults([]);
    setStatus("idle");
    const timer = window.setTimeout(() => inputRef.current?.focus(), 40);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setSearchOpen]);

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

  if (!open) return null;

  const choose = (place: Place) => {
    setSearchOpen(false);
    goToPlace(place);
  };

  const shortlist = recentsForDisplay(recents).slice(0, 4);

  return (
    <div className="absolute inset-0 z-[70] flex animate-pxfade flex-col bg-ground">
      <Command shouldFilter={false} loop className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-none items-center gap-2 border-b border-line bg-surface px-3 py-3">
          <button
            onClick={() => setSearchOpen(false)}
            aria-label="Tutup pencarian"
            className="flex-none rounded-full p-2 text-ink-2 transition-colors hover:bg-surface-2"
          >
            <ArrowLeft size={20} strokeWidth={1.9} />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-[10px] rounded-control bg-surface-2 px-[14px] py-[10px] ring-1 ring-line">
            <Search size={17} strokeWidth={1.9} className="flex-none text-ink-4" />
            <Command.Input
              ref={inputRef}
              value={query}
              onValueChange={setQuery}
              placeholder="Cari halte, tempat, atau alamat"
              className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-3"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                aria-label="Kosongkan"
                className="flex-none text-ink-4 transition-colors hover:text-ink"
              >
                <X size={16} strokeWidth={2} />
              </button>
            )}
          </div>
        </div>

        <Command.List className="min-h-0 flex-1 overflow-y-auto px-3 pb-8 pt-3">
          {query.trim().length < MIN_CHARS ? (
            <>
              {savedPlaces.length > 0 && (
                <Section icon={<Bookmark size={13} strokeWidth={2} />} label="Tersimpan">
                  {savedPlaces.slice(0, 4).map((place) => (
                    <Command.Item
                      key={place.id}
                      value={place.id}
                      onSelect={() => choose(place)}
                      className="rounded-card bg-surface ring-1 ring-line data-[selected=true]:bg-surface-3"
                    >
                      <PlaceRow place={place} />
                    </Command.Item>
                  ))}
                </Section>
              )}

              <Section icon={<Clock size={13} strokeWidth={2} />} label="Terakhir dicari">
                {shortlist.map((entry) => (
                  <Command.Item
                    key={entry.prompt}
                    value={entry.prompt}
                    onSelect={() => {
                      setSearchOpen(false);
                      askFromAnywhere(entry.prompt);
                    }}
                    className="flex cursor-pointer items-center gap-3 rounded-card px-3 py-[13px] data-[selected=true]:bg-surface-3"
                  >
                    <Clock size={17} strokeWidth={1.8} className="flex-none text-ink-4" />
                    <span className="min-w-0 flex-1 truncate text-[15px]">{entry.title}</span>
                  </Command.Item>
                ))}
              </Section>
            </>
          ) : status === "loading" ? (
            <p className="label-sm px-3 py-6 text-ink-3">Mencari…</p>
          ) : status === "failed" ? (
            <EmptyNote
              title="Pencarian tidak bisa dijangkau"
              body="Layanan pencarian sedang tidak merespons. Peta dan agen tetap bisa dipakai — coba lagi sebentar lagi."
            />
          ) : results.length === 0 ? (
            <EmptyNote
              title={`Tidak ada hasil untuk “${query.trim()}”`}
              body="Coba nama halte, stasiun, atau kawasan. Anda juga bisa menanyakannya langsung ke agen."
              action={
                <button
                  onClick={() => {
                    setSearchOpen(false);
                    askFromAnywhere(query.trim());
                  }}
                  className="mt-4 rounded-control bg-ink px-[18px] py-[11px] text-[14px] font-semibold text-surface transition-colors hover:bg-ink/90"
                >
                  Tanyakan ke agen
                </button>
              }
            />
          ) : (
            <Command.Group className="overflow-hidden rounded-card bg-surface ring-1 ring-line">
              {results.map((place) => (
                <Command.Item
                  key={place.id}
                  value={place.id}
                  onSelect={() => choose(place)}
                  className="border-line data-[selected=true]:bg-surface-3 [&+&]:border-t"
                >
                  <PlaceRow place={place} highlight={query.trim()} />
                </Command.Item>
              ))}
            </Command.Group>
          )}
          {results.length > 0 && query.trim().length >= MIN_CHARS && status === "ready" && (
              <p className="label-sm px-3 pt-3 text-ink-3">
                {results.length} hasil dari{" "}
                {results.some((r) => r.kind !== "address")
                  ? "data Pathrix dan alamat"
                  : "pencarian alamat"}
              </p>
          )}
        </Command.List>
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
    <Command.Group className="pb-4">
      <div className="label-sm flex items-center gap-[7px] px-3 pb-2 text-ink-3">
        <span className="text-ink-4">{icon}</span>
        {label}
      </div>
      {children}
    </Command.Group>
  );
}

function EmptyNote({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="px-3 py-8">
      <p className="title-row">{title}</p>
      <p className="body-15 mt-2 max-w-[46ch] text-ink-2">{body}</p>
      {action}
    </div>
  );
}
