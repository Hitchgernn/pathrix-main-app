import { ImageOff } from "lucide-react";

interface PhotoSlotProps {
  src?: string | null;
  alt: string;
  /** Why there is no photo. Shown only when there genuinely is none — field
   *  survey photos land in pangkalan.photo_url, which is empty until
   *  digitization completes. */
  placeholder: string;
  radius?: number;
  className?: string;
  /** Suppresses the explanation while a lookup is still in flight, so the slot
   *  does not say "no photo" and then produce one a moment later. */
  pending?: boolean;
}

export function PhotoSlot({
  src,
  alt,
  placeholder,
  radius = 16,
  className,
  pending = false,
}: PhotoSlotProps) {
  if (src) {
    return (
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className={`h-full w-full object-cover ${className ?? ""}`}
        style={{ borderRadius: radius }}
      />
    );
  }

  return (
    <div
      className={`flex h-full w-full flex-col items-center justify-center gap-2 bg-surface-3 p-3 ${className ?? ""}`}
      style={{ borderRadius: radius }}
    >
      {!pending && (
        <>
          <ImageOff size={18} strokeWidth={1.7} className="text-ink-4" aria-hidden />
          <span className="body-13 max-w-[24ch] text-center text-ink-3">{placeholder}</span>
        </>
      )}
    </div>
  );
}
