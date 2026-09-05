import { Bookmark, Home, Map, Sparkles, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { MessageKey } from "../../i18n";
import type { Tab } from "../../store";

export interface TabDef {
  id: Tab;
  labelKey: MessageKey;
  icon: LucideIcon;
  /** Sidebar grouping on desktop. The mobile bar renders them in one row. */
  group: "utama" | "anda";
}

/** One definition list drives both the mobile tab bar and the desktop sidebar,
 *  so the two can never drift out of order or out of label. */
export const TABS: TabDef[] = [
  { id: "home", labelKey: "nav.home", icon: Home, group: "utama" },
  { id: "explore", labelKey: "nav.explore", icon: Map, group: "utama" },
  { id: "agent", labelKey: "nav.agent", icon: Sparkles, group: "utama" },
  { id: "saved", labelKey: "nav.saved", icon: Bookmark, group: "anda" },
  { id: "profile", labelKey: "nav.profile", icon: User, group: "anda" },
];

export const GROUP_LABEL: Record<TabDef["group"], MessageKey> = {
  utama: "nav.group.main",
  anda: "nav.group.yours",
};
