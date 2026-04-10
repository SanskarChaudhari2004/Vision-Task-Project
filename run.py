"""Entry point script for running the Vision Task server."""
import os

from vision_task import create_app

app = create_app()


def _get_ssl_context():
    """Build SSL context from environment settings.

    Supported options:
    - VISION_TASK_SSL=adhoc -> use Werkzeug self-signed cert for local testing
    - VISION_TASK_SSL_CERT + VISION_TASK_SSL_KEY -> use provided cert/key files
    """
    cert_file = os.environ.get("VISION_TASK_SSL_CERT", "").strip()
    key_file = os.environ.get("VISION_TASK_SSL_KEY", "").strip()
    if cert_file and key_file:
        return (cert_file, key_file)

    ssl_mode = os.environ.get("VISION_TASK_SSL", "off").strip().lower()
    if ssl_mode == "adhoc":
        return "adhoc"
    return None

if __name__ == "__main__":
    debug_mode = os.environ.get("VISION_TASK_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug_mode, ssl_context=_get_ssl_context())
