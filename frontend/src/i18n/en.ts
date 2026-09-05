import type { Messages } from "./index";

/** English. Typed against `id.ts`, so this file will not compile until every
 *  key it defines is present here with a matching call signature.
 *
 *  The do-not-translate list from `id.ts` applies here especially: `andong`,
 *  `becak`, `halte`, `pangkalan`, `TransJogja`, `KRL`, and every Yogyakarta
 *  place name stay as they are. An andong is not a "horse cart" any more than a
 *  gondola is a "boat", and someone reading the English build is standing on
 *  the same street as someone reading the Indonesian one, looking at the same
 *  signage.
 */
export const en: Messages = {
  // --- demo content ---------------------------------------------------------
  "agent.ask": "Ask the agent",

  "quick.route": "Malioboro → Candi Prambanan",
  "quick.cheapest": "Cheapest route to YIA",
  "quick.nearest": "Nearest TransJogja halte",

  "demo.reply.route":
    "Fastest route: walk to the Sosrowijayan becak pangkalan, becak to Stasiun Lempuyangan, KRL Yogya-Solo to Brambanan, then andong to the temple gate. 51 minutes, Rp63,000, 17.1 km in total. I have marked the route on the map.",
  "demo.reply.generic":
    "I need a starting point to work that out. Name where you are now, or tap the location icon on the map. The TransJogja layer is already on, so the halte are visible.",

  "demo.recent1.title": "Candi Prambanan",
  "demo.recent1.prompt": "Malioboro → Candi Prambanan",
  "demo.recent2.title": "Stasiun YIA",
  "demo.recent2.prompt": "Cheapest route to YIA",

  "demo.summary.time": "51 min",
  "demo.summary.fare": "Rp63,000",
  "demo.summary.distance": "17.1 km",
  "demo.summary.transfers": "2 transfers",

  "demo.leg1.mode": "Walk",
  "demo.leg1.sub": "120 m · 2 min · Rp0",
  "demo.leg1.detail":
    "The Malioboro pedestrian way, east side. Walking network from OSMnx; assumed speed 4.5 km/h.",
  "demo.leg2.mode": "Becak",
  "demo.leg2.sub": "2.1 km · 14 min · Rp25,000",
  "demo.leg2.detail":
    "Fare is negotiated. MAPID Apps field survey puts this pangkalan in the Rp20,000-30,000 range. Active 06.00-22.00; becak are modelled as point-to-point links, not fixed routes.",
  "demo.leg3.mode": "KRL Yogya-Solo",
  "demo.leg3.sub": "13.4 km · 22 min · Rp8,000",
  "demo.leg3.detail":
    "Modelled on a ±30 min headway rather than a per-minute timetable. There is no real-time feed for this service. Average waiting time is included.",
  "demo.leg4.mode": "Walk",
  "demo.leg4.sub": "180 m · 2 min · Rp0",
  "demo.leg4.detail": "Leave by the station's west door; the andong pangkalan is across the road.",
  "demo.leg5.mode": "Andong",
  "demo.leg5.sub": "1.3 km · 11 min · Rp30,000",
  "demo.leg5.detail":
    "Fare is negotiated, survey range Rp25,000-35,000. Drops at the East Gate; 6 drivers recorded at this pangkalan.",

  "demo.alt.label": "Cheaper alternative",
  "demo.alt.title": "TransJogja 1A → KRL, no becak",
  "demo.alt.sub": "63 min · Rp45,000 · 640 m more walking",

  "demo.carbon.basis":
    "Basis: 17.1 km by KRL, becak and andong, compared with a private car carrying one passenger over the same distance.",
  "demo.carbon.caveat": "Sample data. Emission factors are not loaded from the database yet.",

  "layer.transit.name": "Public transport",
  "layer.transit.meta": "3 operators, 214 halte",
  "layer.pangkalan.name": "Andong & becak pangkalan",
  "layer.pangkalan.meta": "42 points from field survey",
  "layer.pariwisata.name": "Tourism & culture",
  "layer.pariwisata.meta": "96 points",
  "layer.properti.name": "Property",
  "layer.properti.meta": "310 points from Properti Go",
  "layer.jangkauan.name": "Walking reach",
  "layer.jangkauan.meta": "Isochrones at 5, 10, 15 minutes",
  "layer.bangunan.name": "Buildings",
  "layer.bangunan.meta": "Urban planning, 12% fill",

  // --- navigation ---------------------------------------------------------
  "nav.home": "Home",
  "nav.explore": "Map",
  "nav.agent": "Agent",
  "nav.saved": "Saved",
  "nav.profile": "Profile",
  "nav.group.main": "Navigation",
  "nav.group.yours": "Yours",
  "nav.aria": "Main navigation",
  "nav.collapse": "Collapse navigation",
  "nav.expand": "Expand navigation",
  "nav.thisDevice": "This device",

  // --- home ---------------------------------------------------------------
  "home.greeting": (name: string) => `Hello, ${name}`,
  "home.question": "Where are you going today?",
  "home.carbonMonth": "CO₂e this month",
  "home.openMap": "Open map",
  "home.savedCount": "saved",
  "home.seeAll": "See all",
  "home.recent": "Recent",
  "home.sampleTrips": "Sample trips",
  "home.sampleNote": "Sample trips. Your own history appears here after your first search.",
  "home.savedOnDevice": "Saved on this device",

  "action.route.title": "Find a route",
  "action.route.sub": "Multimodal, door to door",
  "action.stops.title": "Nearest halte",
  "action.stops.sub": "TransJogja, KRL, airport rail",
  "action.pangkalan.title": "Andong & becak",
  "action.pangkalan.sub": "Pangkalan from field survey",
  "action.layers.title": "Map layers",
  "action.layers.sub": "6 thematic layers",

  // --- time ---------------------------------------------------------------
  "time.today": "Today",
  "time.yesterday": "Yesterday",
  "time.daysAgo": (n: number) => `${n} day${n === 1 ? "" : "s"} ago`,

  // --- search -------------------------------------------------------------
  "search.label": "Search places",
  "search.placeholder": "Search a halte, place, or address",
  "search.close": "Close search",
  "search.saved": "Saved",
  "search.recent": "Recent searches",
  "search.searching": "Searching…",
  "search.results": (n: number, local: boolean) =>
    `${n} result${n === 1 ? "" : "s"} from ${local ? "Pathrix data and addresses" : "address search"}`,
  "search.emptyTitle": (q: string) => `No results for “${q}”`,
  "search.emptyBody": "Try the name of a halte, a station, or a neighbourhood.",
  "search.askAgent": "Ask the agent",
  "search.failedTitle": "Search is unreachable",
  "search.failedBody": "The search service is not responding. The map and agent still work.",

  // --- map chrome ---------------------------------------------------------
  "map.styleGroup": "Map style",
  "map.styleLight": "Light map",
  "map.styleDark": "Dark map",
  "map.carbon": "Carbon footprint",
  "map.allLayers": "All layers",
  "map.recenterUser": "Centre on your location",
  "map.recenterCity": "Centre on Yogyakarta",
  "map.yourLocation": "Your location",
  "map.noKey": "Basemap key is not set. Set VITE_MAPID_BASEMAP_KEY to load MAPID Maps.",

  "filter.all": "All",
  "filter.transit": "Halte & KRL",
  "filter.pangkalan": "Andong & becak",
  "filter.tourism": "Tourism",
  "filter.property": "Property",
  "filter.reach": "Walking reach",

  // --- agent --------------------------------------------------------------
  "agent.name": "Pathrix Agent",
  "agent.demoBanner": "Sample mode, agent not wired yet",
  "agent.reading": "Reading the map you are looking at",
  "agent.composing": "Building a route…",
  "agent.calculating": "Calculating…",
  "agent.intro":
    "I read the map you are looking at: active layers, the last route, and the viewport. Name a destination, or ask for something else.",
  "agent.placeholder": "Ask the agent…",
  "agent.inputLabel": "Message for the agent",
  "agent.send": "Send",
  "agent.expand": "Open the full conversation",
  "agent.collapse": "Collapse the conversation",
  "agent.unavailable": "Chat is unavailable right now.",

  "demo.step.readMap": "Reading the map you are looking at",
  "demo.step.endpoints": "Locating the start and destination",
  "demo.step.route": "Building a multimodal route",
  "demo.step.carbon": "Working out fares and carbon",
  "demo.step.nearby": "Looking for nearby halte and pangkalan",
  "demo.step.answer": "Preparing an answer",

  // --- place --------------------------------------------------------------
  "place.detail": "Place details",
  "place.close": "Close",
  "place.routeHere": "Route here",
  "place.share": "Share location",
  "place.askAbout": (name: string) => `Tell me about ${name}`,
  "place.routeTo": (name: string) => `Route to ${name}`,
  "place.details": "Details",
  "place.coordinate": "Coordinates",
  "place.source": "Source",
  "place.photo": "Photo",
  "place.fieldSurvey": "Field survey",
  "place.noPhoto": "No survey photo for this point yet",
  "place.pendingDetails":
    "Opening hours and fares will appear here once the field survey has been digitised.",
  "place.save": (name: string) => `Save ${name}`,
  "place.unsave": (name: string) => `Remove ${name} from saved`,

  "kind.poi": "Place",
  "kind.properti": "Property",
  "kind.transit": "Halte",
  "kind.pangkalan": "Pangkalan",
  "kind.address": "Address",

  "source.address": "Nominatim MAPID",
  "source.pangkalan": "Field survey",
  "source.transit": "Pathrix transit data",
  "source.mission": "MAPID Apps mission",

  "fact.hours": "Opening hours",
  "fact.avgPrice": "Average price",
  "fact.type": "Type",

  // --- saved --------------------------------------------------------------
  "saved.title": "Saved",
  "saved.note": "Kept on this device only. There is no account, and nothing is sent anywhere.",
  "saved.tabPlaces": (n: number) => `Places (${n})`,
  "saved.tabRoutes": (n: number) => `Routes (${n})`,
  "saved.emptyPlacesTitle": "Nothing saved yet",
  "saved.emptyPlacesBody":
    "Tap the heart on any halte, pangkalan, or place on the map to keep it here.",
  "saved.emptyRoutesTitle": "No saved routes yet",
  "saved.emptyRoutesBody":
    "Once the agent has planned a trip, save it from the route card to open it again without asking twice.",
  "saved.openMap": "Open map",
  "saved.askAgent": "Ask the agent",
  "saved.remove": (title: string) => `Remove ${title}`,

  // --- profile ------------------------------------------------------------
  "profile.title": "Profile",
  "profile.nameLabel": "Your name",
  "profile.saveName": "Save name",
  "profile.storedHere": "Kept on this device",
  "profile.trips": "Trips",
  "profile.carbonSample": "CO₂e sample",
  "profile.saved": "Saved",
  "profile.carbonNote":
    "The CO₂e figure still uses sample emission factors. Real values appear once the factors are loaded from the database.",
  "profile.sourcePrefix": (source: string) => `Source: ${source}`,
  "profile.groupMap": "Map",
  "profile.groupData": "Data",
  "profile.groupLanguage": "Language",
  "profile.mapStyle": "Map style",
  "profile.mapStyleSub": "Light or dark",
  "profile.light": "Light",
  "profile.dark": "Dark",
  "profile.location": "Location access",
  "profile.permGranted": "Allowed",
  "profile.permDenied": "Denied",
  "profile.permUnknown": "Not asked yet",
  "profile.permRefresh": "Refresh",
  "profile.permAsk": "Ask permission",
  "profile.language": "App language",
  "profile.languageSub": "Place names stay in their own language",
  "profile.dataSources": "Data sources",
  "profile.dataSourcesSub": "MAPID Apps, OpenStreetMap, field survey",
  "profile.clear": "Clear local data",
  "profile.clearSub": "Profile, saved items, and history",
  "profile.clearAction": "Clear",
  "profile.clearConfirm": "Confirm clear",
  "profile.footer": "Pathrix, Yogyakarta",
  "profile.changeAvatar": "Change profile picture",

  "avatar.pick": "Pick a picture",
  "avatar.option": (seed: string) => `Profile picture ${seed}`,
  "avatar.upload": "Upload a photo",
  "avatar.remove": "Remove",
  "avatar.cancel": "Cancel",
  "avatar.localOnly": "The picture is kept on this device only.",
  "avatar.tooBig": "That photo could not be saved. Try a smaller image.",

  // --- permission ---------------------------------------------------------
  "perm.title": "Allow location access",
  "perm.body":
    "Used to show the nearest halte and andong or becak pangkalan, and to plan a route from where you are.",
  "perm.note":
    "Your location is handled on the device and sent to the server only as a route's starting point. You can change this any time in Profile.",
  "perm.allow": "Allow access",
  "perm.waiting": "Waiting for permission…",
  "perm.later": "Not now, open the Yogyakarta map",

  // --- panels -------------------------------------------------------------
  "panel.layers": "Thematic layers",
  "panel.route": "Malioboro → Prambanan",
  "panel.sustain": "Carbon footprint",
  "panel.close": "Close panel",
  "panel.expand": "Expand panel",
  "panel.shrink": "Shrink panel",

  "layers.note": "Data loads when a layer is switched on, not all at once up front.",
  "layers.notConnected": (meta: string) => `${meta}, not connected yet`,

  "route.transfers": (n: number) => `${n} transfer${n === 1 ? "" : "s"}`,
  "route.saveThis": "Save this route",
  "route.savedHere": "Saved on this device",

  "sustain.avoidedThisTrip": "CO₂e avoided, this trip",
  "sustain.thisMonth": "This month",
  "sustain.tripsRecorded": "Trips recorded",
  "sustain.empty": "No trips recorded yet",
  "sustain.emptyBody":
    "No trips recorded yet. Plan one route and the figure appears here alongside its source.",
  "sustain.factorsReady": "Emission factors ready: KLHK (2023), IPCC 2006 Tier 1.",
  "sustain.sampleRoute": "See a sample route",
  "sustain.sourcePrefix": (source: string) => `Source: ${source}`,
};
