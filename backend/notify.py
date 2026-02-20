"""macOS native notifications."""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def notify(title: str, message: str):
    """Send a macOS notification via osascript. No-op on other platforms."""
    if sys.platform != "darwin":
        logger.debug(f"Notification (non-macOS): {title} — {message}")
        return

    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        logger.debug(f"Notification failed: {e}")
