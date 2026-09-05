import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useT } from "../../i18n";
import { NAV_W, NAV_W_COLLAPSED } from "../../lib/tokens";
import { useStore } from "../../store";
import { Avatar } from "../ui/avatar";
import { GROUP_LABEL, TABS, type TabDef } from "./tabs";

/** The mobile tab bar, promoted. Same five destinations, same order, same
 *  labels — a sidebar because a 1440px screen has the room to keep them named,
 *  not because desktop is a different product (ARCHITECTURE.md §10.3). */
export function NavSidebar() {
  const tab = useStore((s) => s.tab);
  const setTab = useStore((s) => s.setTab);
  const collapsed = useStore((s) => s.navCollapsed);
  const setCollapsed = useStore((s) => s.setNavCollapsed);
  const profile = useStore((s) => s.profile);
  const savedCount = useStore((s) => s.savedPlaces.length + s.savedRoutes.length);
  const t = useT();

  const groups: TabDef["group"][] = ["utama", "anda"];

  return (
    <nav
      aria-label={t("nav.aria")}
      className="absolute inset-y-0 left-0 z-50 flex flex-col border-r border-line bg-surface transition-[width] duration-300 ease-[var(--ease-out-expo)]"
      style={{ width: collapsed ? NAV_W_COLLAPSED : NAV_W }}
    >
      <div className="flex items-center gap-[10px] px-4 pb-5 pt-6">
        <span className="flex h-9 w-9 flex-none items-center justify-center rounded-[11px] bg-ink">
          <PathrixMark />
        </span>
        {!collapsed && (
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[15px] font-bold tracking-[.09em]">PATHRIX</span>
            <span className="label-sm block truncate font-normal text-ink-3">Yogyakarta</span>
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={t(collapsed ? "nav.expand" : "nav.collapse")}
          className="flex-none rounded-[9px] p-[6px] text-ink-4 transition-colors hover:bg-surface-2 hover:text-ink"
          style={collapsed ? { position: "absolute", right: -14, top: 26, background: "#fff" } : undefined}
        >
          {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-3">
        {groups.map((group) => (
          <div key={group}>
            {!collapsed && (
              <div className="label-sm px-3 pb-2 text-ink-3">{t(GROUP_LABEL[group])}</div>
            )}
            <div className="flex flex-col gap-[2px]">
              {TABS.filter((entry) => entry.group === group).map(({ id, labelKey, icon: Icon }) => {
                const active = tab === id;
                return (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? t(labelKey) : undefined}
                    className={`flex items-center gap-[11px] rounded-[11px] px-3 py-[10px] text-left text-[14px] font-medium transition-colors ${
                      active
                        ? "bg-surface-3 text-ink"
                        : "text-ink-2 hover:bg-surface-2 hover:text-ink"
                    } ${collapsed ? "justify-center" : ""}`}
                  >
                    <Icon size={19} strokeWidth={active ? 2.1 : 1.7} className="flex-none" />
                    {!collapsed && <span className="min-w-0 flex-1 truncate">{t(labelKey)}</span>}
                    {!collapsed && id === "saved" && savedCount > 0 && (
                      <span className="figure flex-none rounded-full bg-surface-3 px-2 py-[3px] text-[11px] text-ink-2">
                        {savedCount}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={() => setTab("profile")}
        className={`m-3 flex items-center gap-[10px] rounded-[13px] px-3 py-[10px] text-left transition-colors hover:bg-surface-2 ${
          collapsed ? "justify-center px-0" : ""
        }`}
      >
        <Avatar src={profile.avatar} name={profile.name} className="h-9 w-9" />
        {!collapsed && (
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[14px] font-semibold tracking-[-.01em]">
              {profile.name}
            </span>
            <span className="label-sm block truncate font-normal text-ink-3">{t("nav.thisDevice")}</span>
          </span>
        )}
      </button>
    </nav>
  );
}

/** The brand mark: three stops on one line, which is what the whole product
 *  does. Drawn, not an imported glyph. */
function PathrixMark() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" aria-hidden>
      <path
        d="M5 17.5c0-3 3-3 3-6s-3-3-3-6"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        opacity=".55"
      />
      <path
        d="M11 5.5c4.2 0 4.2 6 0 6s-4.2 6 0 6h8"
        stroke="#fff"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="19" cy="17.5" r="2" fill="#fff" />
    </svg>
  );
}
