"""Anchor the audit chain head and publish it outside the database.

Intended to run nightly, after the day's events have settled. §7.3 wants the
anchor "published somewhere outside this database — a WDEC-held record, a signed
transparency feed"; this command is the mechanism, and ``--sink`` chooses the
destination. The default writes to an append-only file under the state
directory, which is a placeholder for the WORM store rather than a substitute
for it.

Exits non-zero if publication fails, so a scheduler notices. A silently skipped
anchor is a night during which a full chain rewrite would leave no trace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from manobal_core.apps.governance.anchoring import (
    AnchorPublicationError,
    AppendOnlyFileSink,
    publish_anchor,
    unpublished_anchors,
)


class Command(BaseCommand):
    help = "Anchor the audit chain head and publish it to an external sink."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--path",
            type=Path,
            default=Path(getattr(settings, "AUDIT_ANCHOR_PATH", ".state/audit-anchors.jsonl")),
            help="Destination for the append-only file sink.",
        )
        parser.add_argument(
            "--warn-unpublished",
            action="store_true",
            help="Report anchors that were recorded but never externalised.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sink = AppendOnlyFileSink(options["path"])

        try:
            anchor = publish_anchor(sink)
        except AnchorPublicationError as exc:
            raise CommandError(f"MB-7301: anchor publication failed: {exc}") from exc

        if anchor is None:
            self.stdout.write("No audit events to anchor.")
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Anchored event #{anchor.head_event_id} "
                f"({anchor.event_count} events) to {anchor.published_to}."
            )
        )

        if options["warn_unpublished"]:
            stranded = unpublished_anchors()
            if stranded:
                self.stderr.write(
                    self.style.WARNING(
                        f"{len(stranded)} anchor(s) were never externalised. Each is "
                        f"a window in which a full chain rewrite would not be "
                        f"detectable. Oldest: {stranded[0].anchored_at.isoformat()}."
                    )
                )
