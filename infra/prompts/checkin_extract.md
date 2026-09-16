id: checkin_extract
status: signed
model_class: fast
temperature: 0
max_tokens: 160

Extract structured check-in values from session turns.

Return JSON: {"mood": number|null, "energy": number|null, "sleep_quality": number|null, "sleep_hours": number|null, "tags": string[]}.
Nulls are allowed. Do not invent values.
Turns are inside <session> tags.
