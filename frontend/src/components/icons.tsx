export interface GlyphProps {
  size?: number | string;
  strokeWidth?: number | string;
  className?: string;
}

/** Icons the libraries do not have, drawn in lucide's own grammar — 24px box,
 *  currentColor stroke, round caps and joins — so they sit in the same set as
 *  every imported icon rather than reading as clip art. */

export function Carriage({ size = 24, strokeWidth = 1.8, className }: GlyphProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="7" cy="17.8" r="2.7" />
      <circle cx="17.6" cy="18.4" r="1.9" />
      <path d="M4.3 15.1V9.4a1 1 0 0 1 1-1h5.4a1 1 0 0 1 1 1v5.7" />
      <path d="M11.7 12.1h3.1l2.8 4.4" />
      <path d="M4.3 11.9h7.4" />
    </svg>
  );
}

export function Becak({ size = 24, strokeWidth = 1.8, className }: GlyphProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="6.2" cy="17.6" r="2.6" />
      <circle cx="17.8" cy="17.6" r="2.6" />
      <path d="M6.2 15V9.6a1.2 1.2 0 0 1 1.2-1.2h4.4A1.2 1.2 0 0 1 13 9.6V15" />
      <path d="M13 11.6h2.3l2.5 3.6" />
    </svg>
  );
}
