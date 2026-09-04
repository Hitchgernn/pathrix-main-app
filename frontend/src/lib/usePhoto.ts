import { useEffect, useState } from "react";
import { photoFor, type Photo } from "./photos";

/** Resolves a place photograph, or settles on null when there honestly is not
 *  one. `resolved` distinguishes "still looking" from "looked, found nothing",
 *  so a card can hold its shape instead of flashing a placeholder and then
 *  swapping in an image. */
export function usePhoto(name: string | null | undefined): {
  photo: Photo | null;
  resolved: boolean;
} {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [resolved, setResolved] = useState(false);

  useEffect(() => {
    if (!name) {
      setPhoto(null);
      setResolved(true);
      return;
    }
    let cancelled = false;
    setResolved(false);
    void photoFor(name).then((found) => {
      if (cancelled) return;
      setPhoto(found);
      setResolved(true);
    });
    return () => {
      cancelled = true;
    };
  }, [name]);

  return { photo, resolved };
}
