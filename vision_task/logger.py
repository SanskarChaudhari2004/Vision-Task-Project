"""Simple activity logging for demonstration."""
import logging


activity_logger = logging.getLogger("vision_task.activity")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
activity_logger.addHandler(handler)
activity_logger.setLevel(logging.INFO)
