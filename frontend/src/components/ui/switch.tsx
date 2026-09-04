import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "../../lib/cn";

/** The layer toggle. Track is --color-line-strong when off so it reads as an
 *  affordance on white rather than dissolving into the row. */
export function Switch({ className, ...props }: SwitchPrimitive.SwitchProps) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        "relative h-[26px] w-[46px] flex-none rounded-control p-[3px] transition-colors duration-200",
        "bg-line-strong data-[state=checked]:bg-ink",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="block h-5 w-5 rounded-full bg-surface shadow-[0_1px_2px_rgba(16,30,42,.25)] transition-transform duration-200 ease-[var(--ease-snap)] data-[state=checked]:translate-x-5" />
    </SwitchPrimitive.Root>
  );
}
