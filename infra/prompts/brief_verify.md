id: brief_verify
status: signed
model_class: fast
temperature: 0
max_tokens: 160

Compare a brief to the allowed field set. Return JSON {"pass": boolean, "unsupported": string[]}.

A sentence is unsupported if it adds a claim that is not in the field set.

Brief is inside <brief> tags. Fields are inside <fields> tags.
