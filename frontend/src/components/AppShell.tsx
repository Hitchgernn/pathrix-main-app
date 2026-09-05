import { Sparkles } from "lucide-react";
import { NAV_W, NAV_W_COLLAPSED, PANEL_W, TABBAR_GAP, TABBAR_H } from "../lib/tokens";
import { snapPoints, useWindowSize } from "../lib/useWindowSize";
import { useT } from "../i18n";
import { useStore } from "../store";
import { AgentSheet } from "./AgentSheet";
import { MapCanvas } from "./MapCanvas";
import { MapChrome } from "./MapChrome";
import { PanelSheet } from "./PanelSheet";
import { PlaceSheet } from "./place/PlaceSheet";
import { RecenterFab } from "./RecenterFab";
import { NavSidebar } from "./nav/NavSidebar";
import { TabBar } from "./nav/TabBar";
import { HomeScreen } from "./screens/HomeScreen";
import { PermissionScreen } from "./screens/PermissionScreen";
import { ProfileScreen } from "./screens/ProfileScreen";
import { SavedScreen } from "./screens/SavedScreen";

/** The one layout switch in the app.
 *
 *  Both branches render the same five destinations in the same order. Narrow
 *  stacks a screen over the map with a floating tab bar; wide puts the nav in a
 *  sidebar and the screen in a panel beside a map that never leaves the frame.
 *  Desktop is the mobile design promoted, not a second product
 *  (ARCHITECTURE.md §10.3).
 *
 *  The map is mounted once and then only hidden, never unmounted: discarding a
 *  WebGL context and its tile cache on a tab switch costs far more than keeping
 *  it alive behind a screen.
 */
export function AppShell() {
  const tab = useStore((s) => s.tab);
  const wide = useStore((s) => s.wide);
  const mapMounted = useStore((s) => s.mapMounted);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const onboarded = useStore((s) => s.onboarded);
  const agentSnap = useStore((s) => s.agentSnap);
  const dragH = useStore((s) => s.dragH);
  const setTab = useStore((s) => s.setTab);
  const { vh } = useWindowSize();
  const t = useT();

  const onMap = tab === "explore";
  const navW = navCollapsed ? NAV_W_COLLAPSED : NAV_W;
  const agentHeight = dragH ?? snapPoints(vh)[agentSnap];
  const bottomInset = TABBAR_H + TABBAR_GAP + 10;
  // Wide keeps the map in frame under every screen; narrow has no room to, so
  // it only shows through on Explore.
  const mapVisible = mapMounted && (wide || onMap);

  const screen =
    tab === "home" ? (
      <HomeScreen />
    ) : tab === "saved" ? (
      <SavedScreen />
    ) : tab === "profile" ? (
      <ProfileScreen />
    ) : null;

  return (
    <div className="absolute inset-0">
      {mapMounted && (
        <div
          className={mapVisible ? "absolute inset-0" : "absolute inset-0 invisible"}
          aria-hidden={!mapVisible}
        >
          <MapCanvas />
        </div>
      )}

      {wide ? (
        <>
          <NavSidebar />

          {(screen || tab === "agent") && (
            <div
              className="absolute inset-y-0 z-40 flex animate-pxfade flex-col overflow-hidden border-r border-line bg-ground shadow-rail"
              style={{ left: navW, width: PANEL_W }}
            >
              {tab === "agent" ? (
                <AgentSheet variant="panel" height={vh} vh={vh} />
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto">{screen}</div>
              )}
            </div>
          )}

          {onMap && (
            <>
              <MapChrome />
              <RecenterFab bottom={46} />
              <PanelSheet />
              <button
                onClick={() => setTab("agent")}
                className="surface-float absolute bottom-6 z-40 flex items-center gap-[9px] rounded-control px-[18px] py-[13px] text-[14px] font-semibold tracking-[-.01em] shadow-float ring-1 ring-line transition-colors hover:bg-surface"
                style={{ left: navW + 20 }}
              >
                <Sparkles size={17} strokeWidth={1.9} className="text-ink" />
                {t("agent.ask")}
              </button>
            </>
          )}
        </>
      ) : (
        <>
          {screen && (
            <div
              className="absolute inset-0 animate-pxfade overflow-y-auto bg-ground"
              style={{ paddingBottom: bottomInset }}
            >
              {screen}
            </div>
          )}

          {tab === "agent" && (
            <div className="absolute inset-0 bg-ground" style={{ bottom: bottomInset }}>
              <AgentSheet variant="panel" height={vh - bottomInset} vh={vh} />
            </div>
          )}

          {onMap && (
            <>
              <MapChrome />
              <RecenterFab bottom={agentHeight + bottomInset + 12} />
              <AgentSheet
                variant="sheet"
                height={agentHeight}
                vh={vh}
                bottomInset={bottomInset}
              />
              <PanelSheet bottomInset={bottomInset} />
            </>
          )}

          <TabBar />
        </>
      )}

      {onMap && <PlaceSheet />}
      {!onboarded && onMap && <PermissionScreen />}
    </div>
  );
}
