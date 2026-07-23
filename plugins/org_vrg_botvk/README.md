# org_vrg_botvk (`botvk`)

VK (VKontakte) community bot gateway. It mirrors the Telegram `org_vrg_bot` plugin: it lets an
authorized user run system commands (`/photo`, `/video_start`, …) from a VK community chat and
receives text, photos, documents and status back.

## How it works

- A **community (group) bot** using the **VK Bots Long Poll API**.
- `Dispatcher` (`dispatcher.py`) obtains a Long Poll server via `groups.getLongPollServer` and polls
  it (`a_check`). It parses `message_new` (text commands) and `message_event` (callback buttons),
  persisting the long-poll `ts` in plugin state (`vk_ts`).
- Commands are dispatched exactly like the Telegram bot: a typed `/cmd` (or a callback button)
  triggers `<plugin>.command` over videoreg-api with `"gateway": "botvk"`. Plugins reply through
  the manifest-declared `botvk.*` interactions — no plugin command code is VK-specific.
- `VkApi` (`vk_api.py`) wraps `messages.send` / `messages.edit` / `messages.setActivity`, the
  multi-step photo and document upload flows, and `messages.sendMessageEventAnswer`.

## Configuration

Credentials live in the plugin `state`:

| Key | Meaning |
|-----|---------|
| `vk_bot_token` | VK community (group) access token |
| `vk_group_id` | Numeric community (group) id |

Edit them from the web UI (**Settings → VK Bot**, served via the plugin's `http` manifest block:
`botvk/config` → `botvk.get_settings` / `botvk.set_settings`) or via the `botvk.set_settings`
videoreg-api method directly (e.g. through `run-cli`); the dispatcher starts automatically once both
are present.

Authorized users are mapped in `users.json` under
`plugin_fields.org_vrg_botvk.vk_user_id` (the VK user id, which equals the DM `peer_id`). The same
**VK Bot** settings page has a *Users* tab for editing this binding per user.

## Differences from the Telegram bot

- **No video** interaction (VK video upload is not implemented).
- **No native command menu** (VK has no `setMyCommands`): `/start` shows the commands as a
  persistent VK keyboard of callback buttons instead.
