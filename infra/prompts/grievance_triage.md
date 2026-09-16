id: grievance_triage
status: signed
model_class: fast
temperature: 0
max_tokens: 160

Return JSON {"category": string, "urgency": "low"|"medium"|"high", "redacted": string}.

Redact names and contact details from the display text. Grievance text is inside <grievance> tags.
