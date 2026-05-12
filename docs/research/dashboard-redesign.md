# Dashboard redesign

## Context

The Home page currently shows 6 tiles (WiFi/AP, Modem, WireGuard, Camera, Power, Storage). Separately, a "Now" block (`.vrg-state-block`) lives in `index.html` — it's shown on every page in the app shell and contains last media, GPS/LBS links, and quick action buttons (take photo / take short video).

The user wants the Dashboard reorganised:

1. Move the "Now" block (currently in the global app shell) to the Dashboard only, restyle its background/hover to match other tiles, but keep its internal structure intact.
2. Add a new "Поездка" (Trip) block that mirrors the trip/parking header from the Trips page (current trip or parking duration + when the trip started).
3. Rewrite the WiFi, Modem, WireGuard, Camera, Power blocks per the new spec (header always present, content depends on connected/not-connected state, replace emoji icons with the `Icon` component, use specific Material Symbols icons).
4. Drop the Storage tile (already hidden behind `v-if="false"`).
5. The existing endpoint `/api/dashboard/status` must keep doing the job — extend it rather than add a new HTTP endpoint.

## Files to modify

- `plugins/org_vrg_http/static/index.html` — remove the `.vrg-state-block` markup from the app shell; move its state/methods out of the root app instance so it stays only on the Home page.
- `plugins/org_vrg_http/static/js/components/pages/HomeComponent.js` — rebuild the dashboard template (Now / Trip / WiFi / Modem / WireGuard / Power / Camera), use the `Icon` component, restructure the data flow.
- `plugins/org_vrg_http/static/style.css` — restyle `.vrg-state-block` to share the `.dashboard-tile` background/border/hover treatment; add a responsive 2-column grid rule so the Now block spans full width on small/medium screens and 2/3 width on large screens (Trip block fills the remaining 1/3); update `.dashboard-tile-icon` to fit `Icon` SVGs instead of emoji.
- `plugins/org_vrg_http/handlers/dashboard_handlers.py` — add `core.get_trip_state` to the `asyncio.gather` call and include its result in the response.
- `plugins/org_vrg_core/methods/get_trip_state.py` — **new** videoreg-api method (see Backend section). Register it in `plugins/org_vrg_core/plugin_builder.py`.
- `plugins/org_vrg_http/translations/ru.yaml` and `en.yaml` — add the new keys used on the Home page (see i18n section).

## Backend

Add a new videoreg-api method `core.get_trip_state` returning the live trip/parking state computed from the journal. Response shape (state == `null` if no journal events yet):

```python
{
  "state": "in_trip" | "parked" | None,
  "start": "ISO datetime",   # of the current block
}
```

Implementation: read the latest journal file(s) (today, and yesterday if today has no relevant event yet) via `JournalClient`/the same machinery used by `core.get_journal_files`, find the last `charging_on` / `charging_off` event, decide:

- last event == `charging_on` → `state="in_trip"`, `start=event.ts`
- last event == `charging_off` → `state="parked"`, `start=event.ts`

Wire it into the dashboard handler:

```python
trip_state_response = api_client.exec("core.get_trip_state", {})
# add to asyncio.gather and to the response dict as "trip": {...}
```

The duration itself is computed on the frontend (`Date.now() - start`) so the dashboard doesn't drift between requests — matches how `TripsComponent` already does it in `blockDuration` (TripsComponent.js:207–216). Reuse the existing i18n keys `http.trips.duration_h_m` / `duration_h` / `duration_min` / `less_than_min`.

## Frontend

### Layout

Replace the existing `.dashboard-tiles` grid in `HomeComponent.js`. Use a custom CSS-grid layout so Now/Trip live in their own row with the right proportions, and the remaining 5 blocks fall into the auto-fit grid below:

```
[ Now (full / 2/3) ] [ Trip (1/3 on large) ]
[ WiFi ] [ Modem ] [ WireGuard ] [ Power ] [ Camera ]
```

Breakpoint:

- `< 1024px` → Now: 100% width, Trip below it 100% width.
- `>= 1024px` → Now: 2/3, Trip: 1/3.

The lower 5 blocks keep `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))`.

### Blocks

All five "small" blocks share the existing `.dashboard-tile` markup. Replace `<span class="dashboard-tile-icon">📶</span>` with `<icon :name="..." :size="20"></icon>`. Update `.dashboard-tile-icon` CSS to a flex-centered slot that fits SVGs (drop `font-size: 1.25rem`).

**Now block.** Move the existing markup (lines 281–346 of `index.html`) inside the dashboard grid as the first item. Wrap it in `.dashboard-tile.dashboard-tile--now` so it picks up the same background/border/hover as other tiles (override the blue tint currently on `.vrg-state-block`). Keep the header as-is (title `{{ $t('http.now') }}` + chevron toggle when collapsed) — **no leading icon for this block** (per user). Keep collapse behavior, media slot, location rows, action buttons, taken-photos/taken-videos lists untouched.

Move the state and methods (`vrgStateCollapsed`, `statusLoaded`, `statusLastMediaItem`, `gpsLocation`, `lbsLocation`, `takenPhotos`, `takenShortVideos`, `takingPhoto`, `takingShortVideo`, `statusLastMediaReady`, `statusOffline`, `statusLastUpdatedLabel`, `copyToClipboard`, `takePhoto`, `takeShortVideo`) — currently on the root Vue instance in `index.html` — entirely into `HomeComponent`. HomeComponent owns the `/api/dashboard/status` fetch (it already does this) and derives all of the above from the response.

If the root app still needs anything for the layout itself (e.g. `statusBgImageUrl` on `<component :is>`, `statusOffline`/`statusLastUpdatedLabel` if shown in the nav), keep a **separate, minimal** root-level fetch for that — but the Now block's state is fully owned by Home. Verify the root template no longer references the moved properties.

**Trip block.** New tile, icon `map`, title `{{ $t('http.home.trip_title') }}` ("Поездка" / "Trip"). Body:

```
<h-line>{{ tripDurationLabel }}</h-line>    # "Сейчас в пути: 1 ч. 23 м." or "Сейчас на парковке: 14 м."
<meta>{{ tripStartLabel }}</meta>           # "с 09:15 10 мая" — reuse blockTimeStr-style formatting
```

If `trip.state == null` → show "Нет данных" via the existing `http.home.no_data` key. Computed `tripDurationLabel` reuses the formatter from `TripsComponent.blockDuration` (extract into a small helper in HomeComponent — don't import from another page component).

**WiFi.** Header title = either `connections.wifi.ssid` (when connected) or `connections.ap.ssid` (AP mode) or `{{ $t('http.home.disconnected') }}` ("отключено"). Icon `wifi` when any of them is enabled, otherwise `wifi_off`. If connected, show:

```
{{ $t('http.home.type_label') }}: Access Point | Client
IP: {{ ip }}
```

Mode is `Access Point` when `connections.ap.enabled` and not `wifi.enabled`, else `Client`.

**Modem.** Title = `{{ $t('http.settings.modem') }}` ("Модем"). Icon `modem` when connected, `modem_off` otherwise. If `modem.connected == false` → show only `{{ $t('http.home.disconnected') }}` ("Не подключен"). If connected:

```
{{ modem.model }}
{{ modem.operator }} · {{ modem.access_tech }}
IP: {{ connections.modem.ip }}
```

**WireGuard.** Title `WireGuard`, icon `vpn`. If `!wireguard.active` → show `{{ $t('http.home.disconnected') }}`. If active → `IP: {{ wireguard.ip_address }}`.

**Camera.** Title `{{ $t('http.settings.camera') }}` ("Камера"), icon `camera`. Body:

```
{{ $t('http.home.model_label') }}: {{ camera.model || $t('http.home.camera_no_found_short') }}
{{ $t('http.home.record_label') }}: {{ cameraStateLabel }}   # record / pause / stop
```

**Power.** Title `{{ $t('http.settings.power') }}` ("Питание"). Icon logic:

- No battery telemetry (`!power.source.battery_telemetry`) and source is e.g. mains/usb → `power_plug`
- Has telemetry + `power.charging` → `battery_charging`
- Has telemetry + not charging → `battery`

Body:

```
{{ power.source.title }}
{{ $t('http.home.charging_label') }}: {{ power.charging ? $t('http.common.yes') : $t('http.common.no') }}
{{ $t('http.home.charge_label') }}: {{ power.battery_percent }}%   # only if battery_telemetry
```

### Click/navigation

Keep each small tile clickable (`@click="$emit('navigate', '...')"`) to the corresponding settings page. The Now tile is **not** a navigator — keep its internal collapse behavior; the user explicitly said "structure unchanged".

## i18n

Add to `plugins/org_vrg_http/translations/ru.yaml` and `en.yaml` (`http.home.*` namespace):

- `disconnected` — "Не подключен" / "Disconnected"
- `trip_title` — "Поездка" / "Trip"
- `trip_in_progress` — "Сейчас в пути" / "Currently driving"
- `trip_parked` — "Сейчас на парковке" / "Currently parked"
- `type_label` — "Тип" / "Type"
- `model_label` — "Модель" / "Model"
- `charging_label` — "Зарядка" / "Charging"
- `camera_no_found_short` — "не определена" / "not detected"

Reuse existing keys: `http.home.charge_label`, `http.home.record_label`, `http.home.no_data`, `http.home.title`, `http.now`, `http.settings.{camera,modem,power}`, `http.trips.duration_*` / `less_than_min`, `http.common.{yes,no}` (verify these last two exist; add if missing).

## CSS

- Add `.dashboard-grid-now { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr; gap: var(--spacing-md); }` and at `@media (min-width: 1024px) { grid-template-columns: 2fr 1fr; }` — used to lay out Now+Trip as the first row.
- Restyle `.vrg-state-block` (the "Now" block) to use `background: var(--color-bg-secondary)` and `border: 1px solid var(--color-border)` with a hover on `border-color: var(--color-primary)` to match `.dashboard-tile`. Remove the blue-tinted background.
- Update `.dashboard-tile-icon` to a flex-centered 20px slot (drop `font-size: 1.25rem`) so it can host the `Icon` SVG cleanly.

Keep `docs/CSS.md` in sync per the `videoreg-design-system` skill if the changes introduce a new modifier class (`dashboard-tile--now`, `dashboard-grid-now`).

## Verification

1. Open `https://<pi>/` after login. Confirm the Now block no longer appears on `/wifi`, `/modem`, `/power`, etc. — only on the Home page.
2. Confirm all 7 blocks (Now, Trip, WiFi, Modem, WireGuard, Power, Camera) render and use Material Symbols icons (no emoji).
3. Resize the viewport: `<1024px` Now and Trip stack full-width; `>=1024px` they share a row 2/3 + 1/3.
4. Disconnect WiFi (or stop the AP) — WiFi block header switches to "Отключено", icon to `wifi_off`. Same for modem (`modem_off`) and WireGuard.
5. Plug/unplug power, confirm the journal logs a `charging_on`/`charging_off` event (existing behavior). Reload the dashboard — Trip block shows "Сейчас в пути: …" or "Сейчас на парковке: …" with the right duration and start time.
6. Click each small tile, confirm navigation still works (`/wifi`, `/modem`, etc.).
7. Inside the Now block, collapse/expand, take a photo, take a short video — confirm the moved state still works.
8. `journalctl -u vrg-http` / browser devtools — `GET /api/dashboard/status` returns a `trip` field; no new HTTP endpoints were introduced.
