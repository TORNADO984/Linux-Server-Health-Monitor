"""JSON reporter.

Serialises a :class:`HealthReport` to JSON for machine-readable output.
Supports pretty-printing and compact output.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from server_health.models.health import HealthReport

logger = logging.getLogger(__name__)


class _ISODateTimeEncoder(json.JSONEncoder):
    """Custom encoder that handles datetime objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JsonReporter:
    """Serialises a :class:`HealthReport` to JSON."""

    def __init__(self, pretty: bool = True) -> None:
        """Initialise the reporter.

        Args:
            pretty: If True, output indented JSON; otherwise compact JSON.
        """
        self.pretty = pretty

    def render(self, report: HealthReport) -> str:
        """Serialise *report* to a JSON string.

        Args:
            report: The health report to serialise.

        Returns:
            A JSON string representation of the report.
        """
        data = report.to_dict()
        indent = 2 if self.pretty else None
        try:
            return json.dumps(data, indent=indent, cls=_ISODateTimeEncoder, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialise health report to JSON: %s", exc)
            return json.dumps({"error": str(exc)})

    def print(self, report: HealthReport) -> None:
        """Print the JSON representation of *report* to stdout.

        Args:
            report: The health report to print.
        """
        print(self.render(report))
