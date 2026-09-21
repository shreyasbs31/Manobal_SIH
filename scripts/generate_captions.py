#!/usr/bin/env python3
"""
Generate out/manobal_demo_captions_en.srt aligned to master timeline segments.
"""

from pathlib import Path

CAPTIONS = [
    # S1: t=0 to 20
    ("00:00:00,400", "00:00:05,800", "Between 2020 and 2024 the CAPF lost 730\npersonnel to suicide, and 55,555 more resigned."),
    ("00:00:06,000", "00:00:09,500", "Those are MHA's own figures.\nEverything after this is synthetic."),
    ("00:00:09,800", "00:00:15,000", "MANOBAL is built for the weeks before.\nSupport, not surveillance."),

    # S2: t=23 to 45
    ("00:00:23,200", "00:00:29,000", "It begins with twenty seconds. Mood, sleep, and\nonly the context the jawan chooses, in their language."),
    ("00:00:29,300", "00:00:37,500", "It writes to the phone first, so an outpost\nwith no signal keeps working, buffering up to 30 days."),
    ("00:00:37,800", "00:00:41,500", "Their commander never sees it."),

    # S3: t=45 to 74
    ("00:00:45,200", "00:00:48,800", "No one is compared to anyone else."),
    ("00:00:49,000", "00:00:57,500", "Each jawan is measured against their own 90-day norm\nacross seven domains: duty hours, leave, hardship,"),
    ("00:00:57,800", "00:01:03,000", "sleep, self-report, voice and check-in cadence."),
    ("00:01:03,200", "00:01:08,800", "One rough week never flags anyone;\ntwo independent domains have to agree."),
    ("00:01:09,000", "00:01:13,800", "The officer sees which ones fired and a recommended action."),
    ("00:01:14,000", "00:01:18,500", "No score, no rank, no diagnosis."),

    # S4: t=74 to 102
    ("00:01:24,200", "00:01:27,500", "The identity stays locked."),
    ("00:01:27,800", "00:01:35,500", "To reach the person, the officer declares a care\npurpose and writes a justification, and the reveal"),
    ("00:01:35,800", "00:01:39,000", "is logged the instant it happens."),
    ("00:01:39,200", "00:01:46,000", "On their own phone, the jawan sees that their\nidentity was opened, by which role, and why."),
    ("00:01:46,200", "00:01:49,500", "A contact note falls due after access."),

    # S5: t=102 to 126
    ("00:01:42,200", "00:01:46,500", "Command sees companies, never people."),
    ("00:01:46,800", "00:01:52,500", "Any group under ten is blanked, so no one\ncan reason back to an individual."),
    ("00:01:52,800", "00:01:59,000", "Ask the assistant who is under strain and it refuses,\nthen answers only in aggregate."),
    ("00:01:59,200", "00:02:04,000", "The boundary holds inside the AI too."),

    # S6: t=126 to 150
    ("00:02:06,200", "00:02:10,500", "An acute phrase never reaches a language model."),
    ("00:02:10,800", "00:02:18,000", "A deterministic filter runs on the device, ahead\nof any AI, and hands straight to a fixed, reviewed safety screen:"),
    ("00:02:18,200", "00:02:24,000", "Tele-MANAS, a welfare callback, SMS,\nand the jawan's own safety plan."),

    # S7: t=150 to 165
    ("00:02:30,200", "00:02:34,000", "This is what Medical sees."),
    ("00:02:34,200", "00:02:40,500", "A fifteen-minute clock, the minimum context needed to respond,\nno journal text, no assessment answers."),
    ("00:02:40,800", "00:02:44,500", "The next step is a person."),

    # S8: t=165 to 185
    ("00:02:45,200", "00:02:48,500", "Oversight is adversarial by design."),
    ("00:02:48,800", "00:02:56,000", "We tamper with the audit chain; the system catches\nthe break, names its sequence, and restores it."),
    ("00:02:56,200", "00:03:02,500", "Governance can pause Copilot or voice.\nIt cannot switch off the acute path."),

    # S9: t=185 to 207
    ("00:03:05,200", "00:03:10,000", "MANOBAL deliberately does not score suicide risk."),
    ("00:03:10,200", "00:03:15,000", "The published record on those models is poor\nand the stigma is worse."),
    ("00:03:15,200", "00:03:22,000", "It forecasts operational strain instead, measured for precision,\nrecall, calibration and lead time under distribution shift."),
    ("00:03:22,200", "00:03:26,500", "Synthetic validation, not field evidence."),

    # S10: t=207 to 240
    ("00:03:27,200", "00:03:30,000", "Four zones. Analytics holds patterns, no names."),
    ("00:03:30,200", "00:03:35,000", "Names sit in a separate vault, opened only\nfor a justified care contact."),
    ("00:03:35,200", "00:03:40,000", "Zone X, appraisal, promotion, posting,\ndiscipline, has no path in."),
    ("00:03:40,200", "00:03:46,000", "This demo is hosted so you can reach it;\ndeployment runs on the force's own hardware."),
    ("00:03:46,200", "00:03:52,000", "Private self-help, accountable care,\naggregate command, independent oversight."),
    ("00:03:52,200", "00:03:58,000", "Prediction that earns trust\nby refusing to become surveillance."),
]

def main():
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    srt_path = out_dir / "manobal_demo_captions_en.srt"

    lines = []
    for idx, (start, end, text) in enumerate(CAPTIONS, 1):
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated SRT captions: {srt_path}")

if __name__ == "__main__":
    main()
