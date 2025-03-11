import json
import logging
import os
import threading
import time
from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import List
from typing import Optional
from urllib.parse import urljoin

import requests

from galadriel.entities import GALADRIEL_API_BASE_URL
from galadriel.proof.prover import Prover

LOG_EXPORT_INTERVAL_SECONDS = 30
LOG_EXPORT_BATCH_SIZE = 20


class LogsExportHandler(logging.Handler):
    def __init__(
        self,
        logger: logging.Logger,
        prover: Optional[Prover],
        export_interval_seconds: int = LOG_EXPORT_INTERVAL_SECONDS,
    ):
        super().__init__()
        self.logger = logger
        self.prover = prover
        self.log_records: List[str] = []
        self.export_interval_seconds = export_interval_seconds

    def run(self):
        threading.Thread(
            target=self._run_export_logs_job,
            daemon=True,
        ).start()

    def emit(self, record):
        log_entry = self.format(record)
        self.log_records.append(log_entry)

    def _run_export_logs_job(self) -> None:
        """
        Blocking function that exports logs every self.export_interval_seconds
        """
        api_key = os.getenv("GALADRIEL_API_KEY")
        agent_id = os.getenv("AGENT_ID")
        agent_instance_id = os.getenv("AGENT_INSTANCE_ID")
        if not api_key:
            self.logger.info("Didn't find GALADRIEL_API_KEY, skipping logs exporting")
            return
        if not agent_id:
            self.logger.info("AGENT_ID not found, skipping logs exporting")
            return
        if not agent_instance_id:
            self.logger.info("AGENT_INSTANCE_ID not found, skipping logs exporting")
            return
        while True:
            time.sleep(self.export_interval_seconds)
            formatted_logs = self._format_logs()
            is_export_success = self._export_logs(api_key, agent_id, agent_instance_id, formatted_logs)
            if is_export_success:
                self.log_records = self.log_records[len(formatted_logs) :]

    def _format_logs(self) -> List[Dict]:
        logs = self.log_records[:]  # shallow copy
        formatted_logs = []
        for log in logs:
            try:
                log_line = json.loads(log)
                if log_line.get("message"):
                    formatted_logs.append(
                        {
                            "text": log_line["message"],
                            "level": str(log_line.get("levelname", "info")).lower(),
                            "timestamp": self._format_timestamp(log_line.get("asctime")),
                            "signature": self._get_signature(log_line["message"]),
                        }
                    )
            except Exception:
                pass
        return formatted_logs[:LOG_EXPORT_BATCH_SIZE]

    def _format_timestamp(self, asctime: Optional[str]) -> int:
        if not asctime:
            return 0
        try:
            dt_obj = datetime.strptime(asctime, "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=timezone.utc)
            return int(dt_obj.timestamp())
        except Exception:
            return 0

    def _get_signature(self, message: str) -> Optional[str]:
        if not self.prover:
            return None
        hashed = self.prover.hash(message)
        return self.prover.sign(hashed).hex()

    def _export_logs(self, api_key: str, agent_id: str, agent_instance_id: str, formatted_logs: List[Dict]) -> bool:
        is_export_success = False
        if formatted_logs:
            try:
                response = requests.post(
                    urljoin(GALADRIEL_API_BASE_URL, f"v1/agents/logs/{agent_id}"),
                    timeout=60,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json={"agent_instance_id": agent_instance_id, "logs": formatted_logs},
                )
                self.logger.debug(f"Log export request status: {response.status_code}")
                is_export_success = response.ok
            except Exception:
                self.logger.error("Failed to export logs", exc_info=True)
        return is_export_success
