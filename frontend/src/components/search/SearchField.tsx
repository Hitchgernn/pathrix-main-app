import { Search } from "lucide-react";
import { useStore } from "../../store";

interface SearchFieldProps {
  placeholder?: string;
  className?: string;
}

/** The resting search affordance. It is a button, not an input: typing happens
 *  in the overlay, which owns the debounce, the result list and the keyboard
 *  handling, so there is exactly one search implementation in the app. */
export function SearchField({
  placeholder = "Cari halte, tempat, atau alamat",
  className = "",
}: SearchFieldProps) {
  const setSearchOpen = useStore((s) => s.setSearchOpen);

  return (
    <button
      onClick={() => setSearchOpen(true)}
      className={`flex w-full items-center gap-[10px] rounded-control border border-line-strong bg-surface px-[15px] py-[13px] text-left transition-colors hover:border-line-strong ${className}`}
    >
      <Search size={18} strokeWidth={1.9} className="flex-none text-ink-4" />
      <span className="min-w-0 flex-1 truncate text-[15px] text-ink-3">{placeholder}</span>
    </button>
  );
}
