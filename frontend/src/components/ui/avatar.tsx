import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "../../lib/cn";

interface AvatarProps {
  src: string | null;
  name: string;
  className?: string;
}

const initials = (name: string): string =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? "")
    .join("")
    .toUpperCase() || "?";

/** Initials on a warm well are the real fallback, not a grey silhouette:
 *  there is no account system behind this, so there is no stock avatar to
 *  pretend with. */
export function Avatar({ src, name, className }: AvatarProps) {
  return (
    <AvatarPrimitive.Root
      className={cn(
        "relative flex h-10 w-10 flex-none select-none items-center justify-center overflow-hidden rounded-full bg-surface-3",
        className,
      )}
    >
      {src && (
        <AvatarPrimitive.Image src={src} alt={name} className="h-full w-full object-cover" />
      )}
      <AvatarPrimitive.Fallback className="text-[13px] font-semibold tracking-[-.01em] text-ink-2">
        {initials(name)}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}
