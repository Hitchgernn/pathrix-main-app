interface PhotoSlotProps {
  src?: string | null;
  alt: string;
  /** Mono caption shown while no photo exists — field survey photos land in
   *  pangkalan.photo_url, which is empty until digitization completes. */
  placeholder: string;
  radius?: number;
  className?: string;
}

export function PhotoSlot({ src, alt, placeholder, radius = 12, className }: PhotoSlotProps) {
  if (src) {
    return (
      <img
        src={src}
        alt={alt}
        className={`h-full w-full object-cover ${className ?? ""}`}
        style={{ borderRadius: radius }}
      />
    );
  }
  return (
    <div
      className={`flex h-full w-full items-center justify-center border border-dashed border-line bg-surface-2 p-1 ${className ?? ""}`}
      style={{ borderRadius: radius }}
    >
      <span className="kicker text-center text-[9px] leading-tight text-ink-40">{placeholder}</span>
    </div>
  );
}
