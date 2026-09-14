# MANOBAL frontend specification

Field notebook for a force welfare desk. Not a wellness startup, not a hospital EHR.
The first viewport is the job: how am I, what should I do next, who can I call.

## Direction

| Item | Choice |
|---|---|
| Purpose | Daily self-report and a listen-only Talk line on a phone; duty queues on a laptop |
| Audience | Personnel on a small phone at night; officers scanning assigned cases |
| Tone | Calm, institutional, paper and ink. Quiet density on desks. Large targets on the phone |
| Memorable detail | Brass rule + forest rail. Tier is a named picture, never a number |
| Platforms | Expo Go personnel app; Vite web consoles |

## Invariants (do not violate)

- No WSI, numeric welfare score, or token dump in any UI copy
- Helpline numbers appear without opening a case (`recorded: false`)
- Crisis language never reaches a model. Phone holds it and may send SOS
- Voice audio is transcribed on Zone 2. Vendor keys never ship in the app
- Talk replies are two to four short sentences, no diagnosis

## Tokens

Reuse the existing paper/rail palette.

| Token | Value | Use |
|---|---|---|
| ink / ink-soft | `#161c18` / `#4d574f` | Body / secondary |
| paper / raised | `#f3eee3` / `#fbf8f1` | Screen / cards |
| rail | `#1a221e` | Nav, primary buttons |
| brass | `#c4a574` | Active mark only |
| signal / watch / steady | `#9a1f1a` / `#8a5410` / `#27583a` | T4 / T3 / T0–T1 |
| Type | Source Serif 4 (web titles), system UI (phone) | |
| Space | 8px rhythm. Phone tap ≥ 44pt | |

No purple gradients, no nested cards, no decorative blobs.

## Phone — personnel (Expo)

### Pair

- One primary action: Continue as personnel
- Explain: token only, no service number
- Error is a live region. Busy disables the button

### Today

- Eyebrow + “Your picture”
- Large tier code + caption (T0 you only … T4 urgent)
- Why-text as short sentences
- Optional incident check-in offer (not itself a flag)
- Last 7 check-ins as a week strip (mood height). No “score” word
- Primary: Check in today. Secondary: Refresh

### Check-in

- Five scales: mood, sleep, stress, fatigue, connection
- 1–5 chips, 44pt, selected state not colour-only (weight + fill)
- Word under the selected number (e.g. Sleep: Poor → Good)
- One Save. Success: “Saved. This is not a diagnosis.”

### Talk (voice AI)

Pipeline: hold → record (expo-audio) → `POST /v1/me/transcribe` → `prepareTalk` → crisis hold **or** `POST /v1/me/agent` (cloud LLM).

- Chat thread: you (brass-left) and listener (paper)
- Hold-to-talk is the primary control (large target). Release sends
- Typed send remains
- Listening / thinking announced to AT
- If native audio is missing, type still works
- Crisis: on-device notice + SOS. Words are not posted to `/v1/me/agent`

### More

- SOS is the danger action
- Helplines are `tel:` links, shown without a case
- Consent: grant / withdraw per type, no accept-all
- Journal: write + last entries; paused banner at high tier
- Leave this device

## Web — duty consoles

### Gate

- Role cards in a 2–3 column grid
- State whether Talk is on a cloud model or the local listener

### Personnel

- Jump row: Picture, Check-in, Talk, Help, Journal, Questionnaires
- Picture uses TierMark
- Check-in uses the same 1–5 chips as the phone
- Talk is a thread (your line + reply), not a lone reply dump
- Help: helplines as links, SOS danger button

### Officer queue

- Case cards, not a cramped table: tier pill, categories, due, open
- Destination form stays above the list

### Other desks

Keep Commander / WDEC / Clinical structure. Apply tokens, spacing, and empty states only.

## Cloud listener

- `auto`: cloud when `MANOBAL_LLM_API_KEY` is set, else local keywords
- OpenAI-compatible `POST {base}/chat/completions`
- Azure: `api-key` header when the host is `openai.azure.com`, `cognitiveservices.azure.com`, or `services.ai.azure.com`
- Demo bootstrap may use `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + optional deployment/version
- OpenAI (`OPENAI_API_KEY`) and Groq (`GROQ_API_KEY`) also map onto the same Talk client
- Crisis gate still runs before the HTTP call

## Acceptance

| ID | Trigger | Expected |
|---|---|---|
| AC-01 | Open phone Talk | No `ExponentAV` crash; type path always present |
| AC-02 | Hold-to-talk with consent + Deepgram | Transcript appears as “you”, then a listener reply |
| AC-03 | Crisis phrase typed or spoken | On-device notice; `/v1/me/agent` is not called with those words; SOS may fire |
| AC-04 | Cloud key present | Reply is not the sleep-keyword stock sentence for an unrelated prompt |
| AC-05 | Today / check-in | Tier + why render; save check-in returns 201 and confirmation |
| AC-06 | Helpline | Numbers visible; `recorded: false` |
| AC-07 | Web Gate → personnel | Talk thread and chip check-in usable at 375 and 1280 |
| AC-08 | Officer queue | T2/T3/T4 cards open a case; no WSI |

## Out of scope

Store builds, Keycloak login, on-device ML, live FCM/SMS, Hindi on the phone, instruments on the phone.
