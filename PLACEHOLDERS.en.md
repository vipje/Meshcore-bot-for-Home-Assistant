# Reply placeholders of the MeshCore bot

*[Nederlands](PLACEHOLDERS.md)*

Placeholders are words in curly brackets that the bot fills in when it answers. They work in two places:

- the **test** card on the dashboard's **Plugins** page, field *Response format* (the reply to `test`);
- **Advanced → Keyword replies** in the add-on's Configuration tab (`keyword = "reply"`, one per entry).

## All placeholders

| Placeholder | What it becomes | Example |
|---|---|---|
| `{sender}` | Name of the person who sent the message | `Jan` |
| `{connection_info}` | Route, bytes per hop (when known), SNR and RSSI in one go | `a1,b2 (2 hops) \| 1B/hop \| SNR: 6.5 dB \| RSSI: -92 dBm` |
| `{path}` | Only the route | `a1,b2 (2 hops)` |
| `{hops}` | Number of hops (`?` when unknown) | `2` |
| `{hops_label}` | Number of hops as text | `2 hops`, `1 hop` |
| `{bytes_per_hop}` | Bytes per hop of the route: 1, 2 or 3 (`?` when unknown) | `1` |
| `{snr}` | Signal-to-noise ratio, number only: add `dB` yourself | `6.5` |
| `{rssi}` | Signal strength, number only: add `dBm` yourself | `-92` |
| `{timestamp}` | Time the bot received the message | `22:13:34` |
| `{elapsed}` | How long the message was underway | `1234ms` (or "Sync Device Clock" when the clocks differ too much) |
| `{path_distance}` | Distance along the route, when the repeaters' positions are known (else empty) | `12.4km` (or `mi`) |
| `{firstlast_distance}` | Straight distance from first to last repeater, when known (else empty) | `9.8km` |
| `{packet_hash}` | The packet's ID, when known (else empty) | `8f3a1c...` |
| `{phrase_part}` | **test only.** `: ` plus the text typed after `test`, or nothing | `: hello` |
| `{phrase}` | **test only.** The text typed after `test`, without `: ` | `hello` |

## Examples

```text
ack @[{sender}] | {hops_label} | SNR {snr} dB | to Chicago, IL
ack @[{sender}]{phrase_part} | {path} | {elapsed}
```

The standard reply (test card's *Response format* empty) is
`ack @[{sender}]{phrase_part} | {connection_info} | Received at: {timestamp}`.

## Only show a part when it has a value (test card only)

On the test card a placeholder can be followed by a filter: `{name|filter:text}`.

| Filter | What it does | Example |
|---|---|---|
| `prefix_if_nonempty:text` | Puts *text* in front, but only when the value is not empty. Must be the last filter. | `{path_distance\|prefix_if_nonempty: \| Distance: }` |
| `if_nonempty:text` | Shows *text* instead of the value, only when the value is not empty | `{packet_hash\|if_nonempty: (hash known)}` |
| `hops_min:N` | Empty unless the message came over at least N hops (`hops_min:1` drops it for a direct contact) | `{hops_label\|hops_min:1}` |
| `pathbytes_min:N` | Empty unless the route uses at least N bytes per hop | `{path\|pathbytes_min:2}` |

So `ack @[{sender}] | {hops_label}{path_distance|prefix_if_nonempty: | }` adds ` | 12.4km` only when the distance is known.

## Good to know

- Spelling counts, and only the placeholders above exist. In a **keyword reply**, one unknown or misspelled placeholder
  (or a filter, which keyword replies do not support) means the reply is sent exactly as typed, brackets and all.
- `{phrase_part}` and `{phrase}` only work for `test`, not in other keyword replies.
- The test card's *Response format* wins over a `test` keyword.
- A reply longer than one radio message is split into parts; the **LongReplies** card on the Plugins page can shorten
  it instead.
