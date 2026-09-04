import { useState } from "react";
import { Check, Database, MapPinned, Moon, Pencil, Sun, Trash2 } from "lucide-react";
import { requestLocation } from "../../lib/geolocation";
import { SAMPLE_CARBON } from "../../lib/sample";
import { useStore } from "../../store";
import { Avatar } from "../ui/avatar";
import { AvatarPicker } from "../profile/AvatarPicker";

const PERMISSION_LABEL = {
  granted: "Diizinkan",
  denied: "Ditolak",
  unknown: "Belum diminta",
} as const;

/** Who you are on this device, what you have travelled, and the switches that
 *  belong to the whole app rather than to one screen. */
export function ProfileScreen() {
  const profile = useStore((s) => s.profile);
  const setProfile = useStore((s) => s.setProfile);
  const basemap = useStore((s) => s.basemap);
  const setBasemap = useStore((s) => s.setBasemap);
  const permission = useStore((s) => s.locationPermission);
  const setPermission = useStore((s) => s.setLocationPermission);
  const setUserCoord = useStore((s) => s.setUserCoord);
  const savedPlaces = useStore((s) => s.savedPlaces);
  const recents = useStore((s) => s.recents);
  const resetLocalData = useStore((s) => s.resetLocalData);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(profile.name);
  const [confirmReset, setConfirmReset] = useState(false);
  const [pickingAvatar, setPickingAvatar] = useState(false);

  const commit = () => {
    const name = draft.trim();
    if (name) setProfile({ name });
    else setDraft(profile.name);
    setEditing(false);
  };

  return (
    <div className="mx-auto flex w-full max-w-[600px] flex-col px-4 pb-16 pt-6">
      <h1 className="title-lg">Profil</h1>

      <div className="mt-5 rounded-tile bg-surface p-[15px] ring-1 ring-line">
        <div className="flex items-center gap-[14px]">
        <button
          onClick={() => setPickingAvatar((open) => !open)}
          aria-label="Ubah gambar profil"
          aria-expanded={pickingAvatar}
          className="flex-none rounded-full transition-transform active:scale-95"
        >
          <Avatar src={profile.avatar} name={profile.name} className="h-14 w-14" />
        </button>
        <div className="min-w-0 flex-1">
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") commit();
                  if (event.key === "Escape") {
                    setDraft(profile.name);
                    setEditing(false);
                  }
                }}
                maxLength={32}
                aria-label="Nama Anda"
                className="min-w-0 flex-1 rounded-[10px] border border-line-strong bg-surface-2 px-3 py-2 text-[15px] outline-none"
              />
              <button
                onClick={commit}
                aria-label="Simpan nama"
                className="flex-none rounded-full bg-ink p-2 text-surface"
              >
                <Check size={16} strokeWidth={2.2} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => {
                setDraft(profile.name);
                setEditing(true);
              }}
              className="group flex items-center gap-2 text-left"
            >
              <span className="truncate text-[18px] font-semibold tracking-[-.015em]">
                {profile.name}
              </span>
              <Pencil
                size={15}
                strokeWidth={1.9}
                className="flex-none text-ink-4 transition-colors group-hover:text-ink"
              />
            </button>
          )}
          <p className="body-13 mt-[5px] text-ink-3">Tersimpan di perangkat ini</p>
        </div>
        </div>
        {pickingAvatar && <AvatarPicker onClose={() => setPickingAvatar(false)} />}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-[10px]">
        <Stat value={String(recents.length)} label="Perjalanan" />
        <Stat value={SAMPLE_CARBON.month} label="CO₂e contoh" accent />
        <Stat value={String(savedPlaces.length)} label="Tersimpan" />
      </div>
      <p className="body-13 mt-[10px] text-ink-3">
        Angka CO₂e masih memakai faktor emisi contoh. Nilai asli muncul setelah faktor emisi
        dimuat dari basis data.
      </p>
      <p className="body-13 mt-[6px] text-ink-3">Sumber: {SAMPLE_CARBON.source}</p>

      <Group label="Peta">
        <Row
          icon={basemap === "dark" ? <Moon size={18} strokeWidth={1.8} /> : <Sun size={18} strokeWidth={1.8} />}
          title="Tampilan peta"
          sub="Terang atau gelap"
        >
          <div className="flex flex-none gap-[2px] rounded-control bg-surface-2 p-[3px] ring-1 ring-line">
            {(["street", "dark"] as const).map((option) => (
              <button
                key={option}
                onClick={() => setBasemap(option)}
                className={`label-sm rounded-control px-[14px] py-[7px] transition-colors ${
                  basemap === option ? "bg-ink text-surface" : "text-ink-3"
                }`}
              >
                {option === "street" ? "Terang" : "Gelap"}
              </button>
            ))}
          </div>
        </Row>

        <Row
          icon={<MapPinned size={18} strokeWidth={1.8} />}
          title="Akses lokasi"
          sub={PERMISSION_LABEL[permission]}
        >
          <button
            onClick={() =>
              void requestLocation().then((fix) => {
                setPermission(fix.outcome);
                setUserCoord(fix.coord);
              })
            }
            className="label-sm flex-none rounded-control px-[14px] py-[8px] text-ink ring-1 ring-line-strong transition-colors hover:bg-surface-2"
          >
            {permission === "granted" ? "Perbarui" : "Minta izin"}
          </button>
        </Row>
      </Group>

      <Group label="Data">
        <Row
          icon={<Database size={18} strokeWidth={1.8} />}
          title="Sumber data"
          sub="MAPID Apps, OpenStreetMap, survei lapangan"
        />
        <Row
          icon={<Trash2 size={18} strokeWidth={1.8} />}
          title="Hapus data lokal"
          sub="Profil, tersimpan, dan riwayat"
        >
          <button
            onClick={() => {
              if (!confirmReset) {
                setConfirmReset(true);
                return;
              }
              resetLocalData();
              setDraft("Tamu");
              setConfirmReset(false);
            }}
            onBlur={() => setConfirmReset(false)}
            className={`label-sm flex-none rounded-control px-[14px] py-[8px] ring-1 transition-colors ${
              confirmReset
                ? "bg-ink text-surface ring-transparent"
                : "text-ink-2 ring-line-strong hover:bg-surface-2"
            }`}
          >
            {confirmReset ? "Yakin, hapus" : "Hapus"}
          </button>
        </Row>
      </Group>

      <p className="body-13 mt-10 text-center text-ink-3">Pathrix, Yogyakarta</p>
    </div>
  );
}

function Stat({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="rounded-card bg-surface px-3 py-[14px] ring-1 ring-line">
      <p
        className={`figure text-[22px] font-medium leading-none tracking-[-.02em] ${
          accent ? "text-gold-text" : "text-ink"
        }`}
      >
        {value}
      </p>
      <p className="label-sm mt-[7px] font-normal text-ink-3">{label}</p>
    </div>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="label-sm text-ink-3">{label}</h2>
      <div className="mt-2 overflow-hidden rounded-tile bg-surface ring-1 ring-line">{children}</div>
    </section>
  );
}

function Row({
  icon,
  title,
  sub,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  sub: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 px-[15px] py-[14px] [&+&]:border-t [&+&]:border-line">
      <span className="flex h-9 w-9 flex-none items-center justify-center rounded-[11px] bg-surface-2 text-ink-2">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-medium tracking-[-.01em]">{title}</span>
        <span className="mt-[2px] block truncate text-[12.5px] text-ink-3">{sub}</span>
      </span>
      {children}
    </div>
  );
}
