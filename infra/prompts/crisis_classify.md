id: crisis_classify
status: signed
model_class: fast
temperature: 0
max_tokens: 80

Decide if the user text expresses acute distress that needs the safety path.

Return JSON only: {"crisis": boolean, "confidence": number, "category": "direct"|"indirect"|"none"}.

If unsure, set crisis true. Do not answer the user. Do not give advice.
User content is inside <user> tags.
