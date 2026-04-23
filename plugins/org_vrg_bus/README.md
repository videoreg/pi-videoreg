# org_vrg_bus — event bus

Unix socket server. Central bus for message exchange between services and plugins.

Socket: `.videoreg/event-bus.socket`

## Connection architecture

Each **systemd service** (not plugin) opens **one** connection to the bus. All plugins within a service share this connection via `ServiceConnection` (SDK). Each plugin subscribes to its own channels via `subscribe` messages.

## Protocol

Exchange of text strings in JSON format, delimited by `\n`.

### Client → Bus

#### `init`

Connection initialization. Sent as the first message after connecting.

```json
{ "type": "init", "id": "vrg-core" }
```

- `id` — unique service identifier (systemd unit name)

After `init`, the bus automatically subscribes the client to a channel with its own `id` (needed for routing API response messages back to the initiator).

---

#### `subscribe`

Subscribe to one or more channels. Sent after `init`.

```json
{ "type": "subscribe", "channels": ["net", "power", "stat"] }
```

- If the waiting list has queued messages for these channels — they are delivered immediately.
- Re-subscribing to an already subscribed channel is ignored.

---

#### `unsubscribe`

Unsubscribe from channels.

```json
{ "type": "unsubscribe", "channels": ["net"] }
```

---

#### `data`

Send data to a channel.

```json
{ "type": "data", "to": "camera", "data": { "foo": "bar" } }
```

- `to` — recipient channel name
- `data` — arbitrary JSON

If there are no subscribers — the message is placed in the waiting list and stored for up to 15 seconds.

---

### Bus → Client

#### `data` (incoming)

```json
{
  "type": "data",
  "from": "vrg-camera",
  "to": "net",
  "data": { "foo": "bar" },
  "timestamp": 1700000000.0
}
```

- `from` — sender `id` (service)
- `to` — channel the message was sent to

#### `error`

```json
{ "type": "error", "data": { "message": "..." } }
```

Message parsing or processing error.

---

## Channels and routing

- Each client is subscribed to one or more channels.
- The bus delivers `data` messages to all clients that have the given channel in their subscription list.
- The service `id` channel (e.g. `vrg-core`) is automatically subscribed after `init`. Used for routing API responses back to the initiator.

### Typical channel distribution

| Channel | Subscriber |
|---------|------------|
| `bus` | `vrg-core` |
| `core` | `vrg-core` |
| `net` | `vrg-core` |
| `power` | `vrg-core` |
| `stat` | `vrg-core` |
| `camera` | `vrg-camera` |
| `osd` | `vrg-camera` (for OSD data from GPS) |
| `gps` | `vrg-modem` |
| `sms` | `vrg-modem` |
| `bot` | `vrg-bot` |
| `http` | `vrg-http` |

---

## Waiting list

If there are no subscribers for a channel when sending `data`, the message is placed in the waiting list. When a subscriber appears (via `subscribe` or `init`), queued messages are delivered immediately. Messages older than 15 seconds are deleted.

---

## Client lifecycle

```
connect → init → subscribe (plugin channels) → data exchange → disconnect
```

On disconnect, all client subscriptions are automatically removed.
On reconnect, the client repeats `init` + `subscribe`.

---

## SDK: usage in plugins

Plugins do not work with the bus directly. Use `Plugin.init_socket()`:

```python
plugin.init_socket(
    client_id="net",       # default channel for this plugin
    channels=["extra"],    # additional channels (optional)
)
```

The SDK automatically:
- creates one connection per service (`ServiceConnection`)
- sends `init` and `subscribe` on connect
- routes incoming messages to the correct plugin by the `"to"` field

### Sending data

```python
await plugin._connection.send_data(to_channel="camera", data={"foo": "bar"})
# or via easy_connection:
await plugin._easy_connection.send_data(to_channel="camera", data={"foo": "bar"})
```

### API on top of the bus

A request/response layer is implemented on top of the channel protocol (see `sdk/socket/api.py`, `sdk/socket/requests.py`):

```python
# Client
response = await plugin.api_client.exec("net.get_ip", args=None)

# Server (in a plugin method)
plugin.init_api_servier(methods={"get_ip": MethodGetIp(plugin)})
```

The request goes to the `"net"` channel, the response is returned to the `id` channel of the initiating service.
