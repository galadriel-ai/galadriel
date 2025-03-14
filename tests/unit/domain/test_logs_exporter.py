from unittest.mock import MagicMock

from galadriel.domain.logs_exporter import LogsExportHandler
from galadriel.domain import logs_exporter


def get_exporter() -> LogsExportHandler:
    return LogsExportHandler(
        MagicMock(),
        None,
    )


def test_no_env_values():
    logs_exporter.time = MagicMock()

    logs_exporter.os = MagicMock()
    logs_exporter.os.getenv.return_value = None
    exporter: LogsExportHandler = get_exporter()
    exporter._run_export_logs_job()
    logs_exporter.time.sleep.assert_not_called()


def test_formats_logs():
    exporter: LogsExportHandler = get_exporter()
    original_logs = [
        '{"asctime": "2025-01-28 16:04:33,063", "name": "root", "levelname": "INFO", "message": "msg_1", "taskName": null}',
        '{"asctime": "2025-01-28 16:05:33,063", "name": "root", "levelname": "INFO", "message": "msg_2", "taskName": null}',
    ]
    exporter.log_records = original_logs[:]
    formatted = exporter._format_logs()
    assert formatted == [
        {"level": "info", "text": "msg_1", "timestamp": 1738080273, "signature": None},
        {"level": "info", "text": "msg_2", "timestamp": 1738080333, "signature": None},
    ]
    # Does not delete existing values
    assert exporter.log_records == original_logs[:]


def test_formats_logs_with_signature():
    prover = MagicMock()
    exporter: LogsExportHandler = LogsExportHandler(
        MagicMock(),
        prover,
    )
    prover.hash.return_value = b"asdasd"
    prover.sign.return_value = b"asdasd"
    original_logs = [
        '{"asctime": "2025-01-28 16:04:33,063", "name": "root", "levelname": "INFO", "message": "msg_1", "taskName": null}',
        '{"asctime": "2025-01-28 16:05:33,063", "name": "root", "levelname": "INFO", "message": "msg_2", "taskName": null}',
    ]
    exporter.log_records = original_logs[:]
    formatted = exporter._format_logs()
    assert formatted == [
        {"level": "info", "text": "msg_1", "timestamp": 1738080273, "signature": b"asdasd".hex()},
        {"level": "info", "text": "msg_2", "timestamp": 1738080333, "signature": b"asdasd".hex()},
    ]
    # Does not delete existing values
    assert exporter.log_records == original_logs[:]
