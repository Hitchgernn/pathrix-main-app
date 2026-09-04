import { useRef, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import { useStore } from "../../store";
import { Avatar } from "../ui/avatar";

/** DiceBear, keyless and CORS-open. Line-art rather than photographic, which
 *  suits the system and — more to the point — cannot be mistaken for a
 *  photograph of a real person. Only the URL is stored, so a chosen avatar
 *  costs localStorage a few dozen bytes. */
const DICEBEAR = "https://api.dicebear.com/9.x/notionists/svg";
const SEEDS = ["andong", "becak", "malioboro", "prambanan", "kraton", "tugu", "krl", "yia"];

const avatarUrl = (seed: string) =>
  `${DICEBEAR}?seed=${encodeURIComponent(seed)}&backgroundColor=eeeef0`;

/** Longest edge of a stored upload. 256px is enough for a 56px avatar at 3x and
 *  keeps the data URL around 20KB, which localStorage can hold without drama. */
const MAX_EDGE = 256;

/** Downscales through a canvas rather than storing whatever came off the
 *  camera. A modern phone photo is several megabytes; localStorage gives up
 *  around five, and it holds the rest of the profile too. */
function downscale(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("read failed"));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("decode failed"));
      image.onload = () => {
        const scale = Math.min(1, MAX_EDGE / Math.max(image.width, image.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(image.width * scale);
        canvas.height = Math.round(image.height * scale);
        const context = canvas.getContext("2d");
        if (!context) {
          reject(new Error("no 2d context"));
          return;
        }
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.82));
      };
      image.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  });
}

/** Picks the picture that sits beside the local profile. Everything here stays
 *  on the device, in the same `pathrix.v1` key as the rest of it. */
export function AvatarPicker({ onClose }: { onClose: () => void }) {
  const profile = useStore((s) => s.profile);
  const setProfile = useStore((s) => s.setProfile);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    try {
      setProfile({ avatar: await downscale(file) });
      onClose();
    } catch {
      // The one write in this app that can realistically hit quota, so it says
      // so rather than failing silently the way the rest of persist.ts does.
      setError("Foto tidak bisa disimpan. Coba gambar yang lebih kecil.");
    }
  };

  return (
    <div className="mt-3 rounded-tile bg-surface-2 p-[14px] ring-1 ring-line">
      <p className="label-sm text-ink-3">Pilih gambar</p>

      <div className="no-scrollbar -mx-1 mt-2 flex gap-2 overflow-x-auto px-1 pb-1">
        {SEEDS.map((seed) => {
          const url = avatarUrl(seed);
          const active = profile.avatar === url;
          return (
            <button
              key={seed}
              onClick={() => {
                setProfile({ avatar: url });
                onClose();
              }}
              aria-label={`Gambar profil ${seed}`}
              aria-pressed={active}
              className={`flex-none rounded-full transition-transform active:scale-95 ${
                active ? "ring-2 ring-ink ring-offset-2 ring-offset-surface-2" : ""
              }`}
            >
              <Avatar src={url} name={seed} className="h-12 w-12" />
            </button>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(event) => void upload(event.target.files?.[0])}
        />
        <button
          onClick={() => fileRef.current?.click()}
          className="flex items-center gap-[7px] rounded-control bg-ink px-[15px] py-[9px] text-[13px] font-semibold text-surface transition-colors hover:bg-ink/90"
        >
          <Upload size={15} strokeWidth={2} />
          Unggah foto
        </button>
        {profile.avatar && (
          <button
            onClick={() => {
              setProfile({ avatar: null });
              onClose();
            }}
            className="flex items-center gap-[7px] rounded-control px-[15px] py-[9px] text-[13px] font-semibold text-ink-2 ring-1 ring-line-strong transition-colors hover:bg-surface"
          >
            <Trash2 size={15} strokeWidth={1.9} />
            Hapus
          </button>
        )}
        <button
          onClick={onClose}
          className="rounded-control px-[15px] py-[9px] text-[13px] font-semibold text-ink-3 transition-colors hover:text-ink"
        >
          Batal
        </button>
      </div>

      {error && <p className="body-13 mt-2 text-ink-2">{error}</p>}
      <p className="body-13 mt-2 text-ink-3">
        Gambar disimpan di perangkat ini saja.
      </p>
    </div>
  );
}
