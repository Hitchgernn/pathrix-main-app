import { useEffect, useState } from "react";
import { ArrowLeft, MessageCircle, Navigation, Share2, Star } from "lucide-react";
import { askFromAnywhere } from "../../lib/actions";
import { fetchStopDepartures } from "../../lib/api";
import { useT } from "../../i18n";
import { rupiah, surveyDate } from "../../lib/format";
import { KIND_META, transitFromDepartures } from "../../lib/places";
import { NAV_W, NAV_W_COLLAPSED, TABBAR_H } from "../../lib/tokens";
import { usePhoto } from "../../lib/usePhoto";
import { useStore } from "../../store";
import { PhotoSlot } from "../PhotoSlot";
import { FavouriteButton } from "./FavouriteButton";

/** The detail surface for a tapped marker or a chosen search result, following
 *  inspirations/pathrix-inspiration-halte-or-place.png: circular back, centred
 *  title, heart; hero photograph with a glass circular action; a status pill
 *  row; title; outlined fact chips; detail rows; and a sticky footer of one
 *  quiet action beside one filled one.
 *
 *  On mobile it rises from the bottom over the map. On desktop it is the same
 *  card, anchored beside the nav next to the pin the map just flew to.
 */
export function PlaceSheet() {
  const place = useStore((s) => s.selectedPlace);
  const selectPlace = useStore((s) => s.selectPlace);
  const wide = useStore((s) => s.wide);
  const navCollapsed = useStore((s) => s.navCollapsed);
  const { photo, resolved } = usePhoto(place?.name);
  const t = useT();
  const [scheduleState, setScheduleState] = useState<"idle" | "loading" | "error">("idle");

  useEffect(() => {
    setScheduleState("idle");
    if (!place || place.kind !== "transit" || place.transit) return;
    const externalId = place.id.startsWith("transit:") ? place.id.slice("transit:".length) : "";
    if (!externalId) return;

    let cancelled = false;
    setScheduleState("loading");
    const afterLocal = new Date().toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Jakarta",
    });
    void fetchStopDepartures(externalId, afterLocal)
      .then((departures) => {
        if (cancelled) return;
        const current = useStore.getState().selectedPlace;
        if (!current || current.id !== place.id) return;
        useStore.getState().selectPlace({
          ...current,
          transit: transitFromDepartures(departures),
        });
        setScheduleState("idle");
      })
      .catch(() => {
        if (!cancelled) setScheduleState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [place?.id, place?.kind, Boolean(place?.transit)]);

  if (!place) return null;

  const meta = KIND_META[place.kind];
  const coords = `${place.coord[1].toFixed(5)}, ${place.coord[0].toFixed(5)}`;
  const hero = place.photoUrl ?? photo?.url ?? null;
  // The post's own photographs, minus the one already filling the hero.
  const strip = (place.photos ?? []).filter((url) => url !== hero);
  const surveyedAt = place.survey?.at ? surveyDate(place.survey.at) : null;
  const hasSurvey = Boolean(place.description || place.survey?.by || surveyedAt);
  const transit = place.transit;

  const source = t(
    place.kind === "address"
      ? "source.address"
      : place.kind === "pangkalan"
        ? "source.pangkalan"
        : place.kind === "transit"
          ? "source.transit"
          : "source.mission",
  );

  const position = wide
    ? {
        left: (navCollapsed ? NAV_W_COLLAPSED : NAV_W) + 20,
        top: 128,
        width: 372,
        maxHeight: "calc(100% - 176px)",
      }
    : {
        left: 12,
        right: 12,
        bottom: `calc(env(safe-area-inset-bottom, 0px) + ${TABBAR_H + 22}px)`,
        maxHeight: "78%",
      };

  return (
    <section
      aria-label={place.name}
      className="absolute z-[60] flex animate-pxrise flex-col overflow-hidden rounded-sheet bg-surface shadow-float ring-1 ring-line"
      style={position}
    >
      <header className="flex flex-none items-center gap-2 px-3 pb-2 pt-3">
        <button
          onClick={() => selectPlace(null)}
          aria-label={t("place.close")}
          className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-surface-3 transition-colors hover:bg-line-strong"
        >
          <ArrowLeft size={19} strokeWidth={1.9} />
        </button>
        <h2 className="title-row min-w-0 flex-1 truncate text-center">{t("place.detail")}</h2>
        <FavouriteButton place={place} />
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <div className="relative">
          <div className="h-[168px] w-full overflow-hidden rounded-card">
            <PhotoSlot
              src={hero}
              alt={place.name}
              placeholder={t("place.noPhoto")}
              radius={20}
              pending={!resolved}
            />
          </div>

          {hero && (
            <button
              onClick={() => askFromAnywhere(t("place.askAbout", place.name))}
              aria-label={t("place.askAbout", place.name)}
              className="surface-float absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full shadow-card"
            >
              <MessageCircle size={16} strokeWidth={1.9} />
            </button>
          )}
        </div>

        {/* The reference pairs a status pill with a rating pill under the hero.
            Ours carry the two things we can stand behind: what kind of place
            this is, and whether a surveyor actually stood there. */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="label-sm rounded-control bg-surface-3 px-[11px] py-[6px] text-ink-2">
            {t(meta.labelKey)}
          </span>
          {/* The gold says a person stood there, and now names whose survey it
              was: the andong/becak stands arrive from the MAPID activity feed,
              so claiming our own field survey for them would be false. */}
          {(place.survey?.community || place.kind === "pangkalan") && (
            <span className="label-sm flex items-center gap-[5px] rounded-control bg-surface px-[11px] py-[6px] text-gold-text ring-1 ring-line">
              <Star size={13} strokeWidth={0} fill="var(--color-gold)" aria-hidden />
              {t(place.survey?.community ? "place.communitySurvey" : "place.fieldSurvey")}
            </span>
          )}
        </div>

        <h3 className="title-lg mt-3">{place.name}</h3>
        {place.subtitle && <p className="body-13 mt-[6px] text-ink-2">{place.subtitle}</p>}

        {/* A halte condition survey is prose, not fields: shelter type, roof,
            ramp, guiding block, pavement. Rendered whole and as written —
            summarising someone's survey would be us inventing the summary. */}
        {place.description && (
          <>
            <h4 className="label-sm mt-[20px]">{t("place.surveyNote")}</h4>
            <p className="body-13 mt-[6px] whitespace-pre-line text-ink-2">{place.description}</p>
          </>
        )}

        {strip.length > 0 && (
          <div
            aria-label={t("place.photos", strip.length + 1)}
            className="no-scrollbar mt-[14px] flex gap-2 overflow-x-auto"
          >
            {strip.map((url) => (
              <img
                key={url}
                src={url}
                alt=""
                loading="lazy"
                className="h-[68px] w-[92px] flex-none rounded-card object-cover ring-1 ring-line"
              />
            ))}
          </div>
        )}

        {place.facts.length > 0 && (
          <div className="mt-[14px] flex flex-wrap gap-[6px]">
            {place.facts.map((fact) => (
              <span
                key={fact.labelKey}
                className="rounded-control border border-line-strong px-[12px] py-[7px] text-[13px] text-ink-2"
              >
                {t(fact.labelKey)}: <span className="figure text-ink">{fact.value}</span>
              </span>
            ))}
          </div>
        )}

        {place.kind === "transit" && !transit && scheduleState !== "idle" && (
          <p className="body-13 mt-[18px] text-ink-3" role={scheduleState === "error" ? "alert" : "status"}>
            {t(scheduleState === "error" ? "transit.scheduleError" : "transit.loadingSchedule")}
          </p>
        )}

        {transit && (
          <section className="mt-[22px]" aria-labelledby="transit-schedule-heading">
            <h4 id="transit-schedule-heading" className="label-sm">
              {t("transit.routes")}
            </h4>

            {transit.routes.length > 0 ? (
              <div className="mt-1">
                {transit.routes.map((service, index) => {
                  const departures = service.next_departures ?? [];
                  const effectiveFrom = service.effective_from ?? transit.effectiveFrom;
                  const effectiveUntil = service.effective_until ?? transit.effectiveUntil;
                  const freshness = service.freshness_status ?? transit.freshnessStatus;
                  const source = service.source ?? transit.source;
                  const serviceName = service.name ?? String(service.route_id ?? index + 1);
                  const headwayMin = service.headway_min_minutes ?? service.headway_min;
                  const headwayMax = service.headway_max_minutes ?? headwayMin;
                  const headway =
                    headwayMin != null && headwayMax != null && headwayMin !== headwayMax
                      ? t("transit.headwayRange", headwayMin, headwayMax)
                      : headwayMin != null
                        ? t("transit.headway", headwayMin)
                        : null;
                  const serviceHours =
                    service.service_start_local && service.service_end_local
                      ? t(
                          "transit.serviceHours",
                          service.service_start_local,
                          service.service_end_local,
                        )
                      : null;
                  const meta = [
                    service.operator,
                    serviceHours,
                    headway,
                    service.headway_is_approximate ? t("transit.approximate") : null,
                    service.fare_idr != null ? t("transit.fare", rupiah(service.fare_idr)) : null,
                  ].filter(Boolean);

                  return (
                    <article
                      key={String(service.route_id ?? `${serviceName}-${index}`)}
                      className="hairline py-[12px]"
                    >
                      <h5 className="title-row break-words">{serviceName}</h5>
                      {meta.length > 0 && (
                        <p className="body-13 mt-[3px] break-words text-ink-2">{meta.join(" · ")}</p>
                      )}
                      {departures.length > 0 && (
                        <p className="figure mt-[6px] break-words text-[12px] text-ink">
                          {t("transit.nextDepartures", departures.slice(0, 5).join(" · "))}
                        </p>
                      )}
                      {service.service_basis && (
                        <p className="body-13 mt-[3px] break-words text-ink-3">
                          {t("transit.scheduleBasis", service.service_basis)}
                        </p>
                      )}
                      {(effectiveFrom || effectiveUntil) && (
                        <p className="body-13 mt-[5px] break-words text-ink-3">
                          {[
                            effectiveFrom ? t("transit.effectiveFrom", effectiveFrom) : null,
                            effectiveUntil ? t("transit.effectiveUntil", effectiveUntil) : null,
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        </p>
                      )}
                      {freshness && (
                        <p className="body-13 mt-[3px] break-words text-ink-3">
                          {t("transit.freshness", freshness)}
                        </p>
                      )}
                      {source && (
                        <p className="body-13 mt-[3px] break-words text-ink-3">
                          {t("transit.source")}: {source}
                        </p>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : transit.schedule ? (
              <div className="hairline mt-1 py-[12px]">
                {(transit.schedule.next_departures?.length ?? 0) > 0 && (
                  <p className="figure break-words text-[12px] text-ink">
                    {t(
                      "transit.nextDepartures",
                      transit.schedule.next_departures!.slice(0, 5).join(" · "),
                    )}
                  </p>
                )}
                {transit.schedule.headway_min != null && (
                  <p className="body-13 mt-[3px] text-ink-2">
                    {t("transit.headway", transit.schedule.headway_min)}
                  </p>
                )}
                {(transit.effectiveFrom || transit.effectiveUntil) && (
                  <p className="body-13 mt-[5px] break-words text-ink-3">
                    {[
                      transit.effectiveFrom
                        ? t("transit.effectiveFrom", transit.effectiveFrom)
                        : null,
                      transit.effectiveUntil
                        ? t("transit.effectiveUntil", transit.effectiveUntil)
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  </p>
                )}
                {transit.freshnessStatus && (
                  <p className="body-13 mt-[3px] break-words text-ink-3">
                    {t("transit.freshness", transit.freshnessStatus)}
                  </p>
                )}
                {transit.source && (
                  <p className="body-13 mt-[3px] break-words text-ink-3">
                    {t("transit.source")}: {transit.source}
                  </p>
                )}
              </div>
            ) : (
              <p className="body-13 mt-[6px] text-ink-3">{t("transit.noSchedule")}</p>
            )}
          </section>
        )}

        <h4 className="label-sm mt-[22px]">{t("place.details")}</h4>
        <dl className="mt-1">
          <Row label={t("place.coordinate")} value={coords} mono />
          <Row label={t("place.source")} value={source} />
          {place.survey?.by && <Row label={t("place.surveyedBy")} value={place.survey.by} />}
          {place.survey?.community && (
            <Row label={t("place.community")} value={place.survey.community} />
          )}
          {surveyedAt && <Row label={t("place.surveyedAt")} value={surveyedAt} mono />}
          {photo && !place.photoUrl && <Row label={t("place.photo")} value={photo.credit} href={photo.href} />}
        </dl>

        {place.facts.length === 0 && !hasSurvey && !transit && place.kind !== "address" && (
          <p className="body-13 mt-[14px] text-ink-3">
            {t("place.pendingDetails")}
          </p>
        )}
      </div>

      <div className="flex flex-none items-center gap-[10px] border-t border-line px-3 pb-[16px] pt-[14px]">
        <button
          onClick={() => {
            const text = `${place.name}, ${coords}`;
            if (navigator.share) void navigator.share({ title: place.name, text }).catch(() => {});
            else void navigator.clipboard?.writeText(text).catch(() => {});
          }}
          aria-label={t("place.share")}
          className="flex h-[50px] w-[50px] flex-none items-center justify-center rounded-control border border-line-strong text-ink-2 transition-colors hover:bg-surface-2"
        >
          <Share2 size={17} strokeWidth={1.9} />
        </button>
        <button
          onClick={() => askFromAnywhere(t("place.routeTo", place.name))}
          className="flex h-[50px] flex-1 items-center justify-center gap-[9px] rounded-control bg-ink text-[15px] font-semibold tracking-[-.01em] text-surface transition-[background-color,transform] hover:bg-ink/90 active:scale-[.985]"
        >
          <Navigation size={17} strokeWidth={2} />
          {t("place.routeHere")}
        </button>
      </div>
    </section>
  );
}

function Row({
  label,
  value,
  mono,
  href,
}: {
  label: string;
  value: string;
  mono?: boolean;
  href?: string;
}) {
  return (
    <div className="hairline flex items-baseline justify-between gap-4 py-[11px]">
      <dt className="label-sm flex-none font-normal text-ink-3">{label}</dt>
      <dd className={`min-w-0 truncate text-right text-[13px] text-ink-2 ${mono ? "figure" : ""}`}>
        {href ? (
          <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
            {value}
          </a>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}
