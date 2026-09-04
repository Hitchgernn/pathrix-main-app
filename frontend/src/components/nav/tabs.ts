import { Bookmark, Home, Map, Sparkles, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Tab } from "../../store";

export interface TabDef {
  id: Tab;
  label: string;
  icon: LucideIcon;
  /** Sidebar grouping on desktop. The mobile bar renders them in one row. */
  group: "utama" | "anda";
}

/** One definition list drives both the mobile tab bar and the desktop sidebar,
 *  so the two can never drift out of order or out of label. */
export const TABS: TabDef[] = [
  { id: "home", label: "Beranda", icon: Home, group: "utama" },
  { id: "explore", label: "Peta", icon: Map, group: "utama" },
  { id: "agent", label: "Agen", icon: Sparkles, group: "utama" },
  { id: "saved", label: "Tersimpan", icon: Bookmark, group: "anda" },
  { id: "profile", label: "Profil", icon: User, group: "anda" },
];

export const GROUP_LABEL: Record<TabDef["group"], string> = {
  utama: "Navigasi",
  anda: "Milik Anda",
};
