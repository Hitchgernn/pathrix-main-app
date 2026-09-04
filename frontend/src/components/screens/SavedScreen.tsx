import { Bookmark, Map, Trash2 } from "lucide-react";
import { askFromAnywhere, goToPlace } from "../../lib/actions";
import { useStore } from "../../store";
import { PlaceRow } from "../place/PlaceRow";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

/** Everything this device has kept. Two lists, because a place and an itinerary
 *  are answers to different questions and mixing them makes both harder to
 *  scan. */
export function SavedScreen() {
  const savedPlaces = useStore((s) => s.savedPlaces);
  const savedRoutes = useStore((s) => s.savedRoutes);
  const toggleSavedRoute = useStore((s) => s.toggleSavedRoute);
  const setTab = useStore((s) => s.setTab);

  return (
    <div className="mx-auto flex w-full max-w-[600px] flex-col px-4 pb-16 pt-6">
      <h1 className="title-lg">Tersimpan</h1>
      <p className="body-13 mt-[7px] text-ink-3">
        Disimpan di perangkat ini saja — tidak ada akun dan tidak dikirim ke mana pun.
      </p>

      <Tabs defaultValue="tempat" className="mt-5">
        <TabsList>
          <TabsTrigger value="tempat">Tempat ({savedPlaces.length})</TabsTrigger>
          <TabsTrigger value="rute">Rute ({savedRoutes.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="tempat">
          {savedPlaces.length === 0 ? (
            <EmptyState
              icon={<Bookmark size={22} strokeWidth={1.7} />}
              title="Belum ada tempat tersimpan"
              body="Ketuk ikon hati pada halte, pangkalan, atau tempat mana pun di peta untuk menyimpannya di sini."
              cta="Buka peta"
              onCta={() => setTab("explore")}
            />
          ) : (
            <div className="-mx-3">
              {savedPlaces.map((place) => (
                <PlaceRow key={place.id} place={place} onClick={() => goToPlace(place)} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="rute">
          {savedRoutes.length === 0 ? (
            <EmptyState
              icon={<Map size={22} strokeWidth={1.7} />}
              title="Belum ada rute tersimpan"
              body="Setelah agen menyusun perjalanan, simpan rutenya dari kartu rute agar bisa dibuka lagi tanpa bertanya ulang."
              cta="Tanya agen"
              onCta={() => setTab("agent")}
            />
          ) : (
            <div>
              {savedRoutes.map((route) => (
                <div
                  key={route.id}
                  className="hairline flex items-center gap-3 py-[13px]"
                >
                  <button
                    onClick={() => askFromAnywhere(route.prompt)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <span className="block truncate text-[15px] font-semibold tracking-[-.01em]">
                      {route.title}
                    </span>
                    <span className="figure mt-[4px] block truncate text-[12px] text-ink-3">{route.meta}</span>
                  </button>
                  <button
                    onClick={() => toggleSavedRoute(route)}
                    aria-label={`Hapus ${route.title}`}
                    className="flex-none rounded-full p-2 text-ink-4 transition-colors hover:bg-surface-3 hover:text-ink"
                  >
                    <Trash2 size={17} strokeWidth={1.8} />
                  </button>
                </div>
              ))}
              <div className="hairline" />
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  body,
  cta,
  onCta,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  cta: string;
  onCta: () => void;
}) {
  return (
    <div className="mt-2 rounded-tile bg-surface px-5 py-9 text-center ring-1 ring-line">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-[15px] bg-surface-3 text-ink">
        {icon}
      </span>
      <p className="title-row mt-4">{title}</p>
      <p className="body-13 mx-auto mt-2 max-w-[36ch] text-ink-2">{body}</p>
      <button
        onClick={onCta}
        className="mt-5 rounded-control bg-ink px-[20px] py-[11px] text-[14px] font-semibold text-surface transition-colors hover:bg-ink/90"
      >
        {cta}
      </button>
    </div>
  );
}
