# Plaatsaanduidingen in antwoorden van de MeshCore-bot

*[English](PLACEHOLDERS.en.md)*

Plaatsaanduidingen (placeholders) zijn woorden tussen accolades die de bot invult als hij antwoordt. Ze werken op twee
plekken:

- de kaart **test** op de pagina **Plugins** van het dashboard, veld *Response format* (het antwoord op `test`);
- **Advanced → Keyword replies** in het tabblad Configuratie van de add-on (`keyword = "antwoord"`, één per regel).

## Alle plaatsaanduidingen

| Plaatsaanduiding | Wordt | Voorbeeld |
|---|---|---|
| `{sender}` | Naam van wie het bericht stuurde | `Jan` |
| `{connection_info}` | Route, bytes per hop (als bekend), SNR en RSSI in één keer | `a1,b2 (2 hops) \| 1B/hop \| SNR: 6.5 dB \| RSSI: -92 dBm` |
| `{path}` | Alleen de route | `a1,b2 (2 hops)` |
| `{hops}` | Aantal hops (`?` als onbekend) | `2` |
| `{hops_label}` | Aantal hops als tekst | `2 hops`, `1 hop` |
| `{bytes_per_hop}` | Bytes per hop van de route: 1, 2 of 3 (`?` als onbekend) | `1` |
| `{snr}` | Signaal-ruisverhouding, alleen het getal: zet er zelf `dB` achter | `6.5` |
| `{rssi}` | Signaalsterkte, alleen het getal: zet er zelf `dBm` achter | `-92` |
| `{timestamp}` | Tijd waarop de bot het bericht ontving | `22:13:34` |
| `{elapsed}` | Hoe lang het bericht onderweg was | `1234ms` (of "Sync Device Clock" als de klokken te ver uit elkaar lopen) |
| `{path_distance}` | Afstand langs de route, als de posities van de repeaters bekend zijn (anders leeg) | `12.4km` (of `mi`) |
| `{firstlast_distance}` | Afstand in rechte lijn van eerste naar laatste repeater, als bekend (anders leeg) | `9.8km` |
| `{packet_hash}` | ID van het pakket, als bekend (anders leeg) | `8f3a1c...` |
| `{phrase_part}` | **Alleen test.** `: ` plus de tekst die na `test` getypt is, of niets | `: hallo` |
| `{phrase}` | **Alleen test.** De tekst na `test`, zonder `: ` | `hallo` |

## Voorbeelden

```text
ack @[{sender}] | {hops_label} | SNR {snr} dB | vanuit Maastricht
ack @[{sender}]{phrase_part} | {path} | {elapsed}
```

Het standaardantwoord (*Response format* op de test-kaart leeg) is
`ack @[{sender}]{phrase_part} | {connection_info} | Received at: {timestamp}`.

## Een deel alleen tonen als het een waarde heeft (alleen test-kaart)

Op de test-kaart kan achter een plaatsaanduiding een filter staan: `{naam|filter:tekst}`.

| Filter | Wat het doet | Voorbeeld |
|---|---|---|
| `prefix_if_nonempty:tekst` | Zet *tekst* ervoor, maar alleen als de waarde niet leeg is. Moet het laatste filter zijn. | `{path_distance\|prefix_if_nonempty: \| Afstand: }` |
| `if_nonempty:tekst` | Toont *tekst* in plaats van de waarde, alleen als de waarde niet leeg is | `{packet_hash\|if_nonempty: (hash bekend)}` |
| `hops_min:N` | Leeg tenzij het bericht over minstens N hops kwam (`hops_min:1` laat het weg bij direct contact) | `{hops_label\|hops_min:1}` |
| `pathbytes_min:N` | Leeg tenzij de route minstens N bytes per hop gebruikt | `{path\|pathbytes_min:2}` |

Dus `ack @[{sender}] | {hops_label}{path_distance|prefix_if_nonempty: | }` zet er alleen ` | 12.4km` achter als de
afstand bekend is.

## Goed om te weten

- Spelling telt, en alleen de plaatsaanduidingen hierboven bestaan. In een **keyword-antwoord** zorgt één onbekende of
  verkeerd gespelde plaatsaanduiding (of een filter, dat keyword-antwoorden niet kennen) ervoor dat het antwoord letterlijk
  wordt verstuurd, accolades en al.
- `{phrase_part}` en `{phrase}` werken alleen bij `test`, niet in andere keyword-antwoorden.
- *Response format* op de test-kaart gaat voor een `test`-keyword.
- Een antwoord dat langer is dan één radiobericht wordt in delen gestuurd; met de kaart **LongReplies** op de pagina
  Plugins kun je het in plaats daarvan inkorten.
