import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../lib/cn";

/** Radix tabs in the app's own vocabulary: a pill track on --color-surface-2
 *  with the active pill in white. Radix is here for the roving-tabindex and
 *  arrow-key behaviour a hand-rolled row does not get for free. */

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: TabsPrimitive.TabsListProps) {
  return (
    <TabsPrimitive.List
      className={cn(
        "flex gap-1 rounded-control bg-surface-2 p-1 ring-1 ring-line",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({ className, ...props }: TabsPrimitive.TabsTriggerProps) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "flex-1 rounded-control px-4 py-2 text-[13px] font-semibold tracking-[-.01em] text-ink-3 transition-colors",
        "data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-card",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({ className, ...props }: TabsPrimitive.TabsContentProps) {
  return <TabsPrimitive.Content className={cn("mt-4 outline-none", className)} {...props} />;
}
