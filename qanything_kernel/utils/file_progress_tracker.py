from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from qanything_kernel.utils.custom_log import insert_logger, debug_logger


class FileStage(Enum):
    UPLOAD = "upload"
    PARSE = "parse"
    CHUNK = "chunk"
    MILVUS_INSERT = "milvus_insert"
    ES_INDEX = "es_index"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class FileStageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ErrorCode(Enum):
    UNKNOWN_ERROR = "E000"
    UPLOAD_TOO_LARGE = "E001"
    UPLOAD_FORMAT_UNSUPPORTED = "E002"
    PARSE_TIMEOUT = "E101"
    PARSE_EMPTY_CONTENT = "E102"
    PARSE_CONTENT_TOO_LARGE = "E103"
    PARSE_ERROR = "E104"
    PARSE_ANTI_CRAWL = "E105"
    CHUNK_ERROR = "E201"
    MILVUS_TIMEOUT = "E301"
    MILVUS_CONNECTION_ERROR = "E302"
    MILVUS_INSERT_ERROR = "E303"
    ES_TIMEOUT = "E401"
    ES_CONNECTION_ERROR = "E402"
    ES_INDEX_ERROR = "E403"
    ROLLBACK_ERROR = "E501"


RETRYABLE_ERRORS = {
    ErrorCode.MILVUS_TIMEOUT,
    ErrorCode.MILVUS_CONNECTION_ERROR,
    ErrorCode.MILVUS_INSERT_ERROR,
    ErrorCode.ES_TIMEOUT,
    ErrorCode.ES_CONNECTION_ERROR,
    ErrorCode.ES_INDEX_ERROR,
    ErrorCode.PARSE_TIMEOUT,
    ErrorCode.UNKNOWN_ERROR,
}


STAGE_WEIGHTS = {
    FileStage.UPLOAD: 5,
    FileStage.PARSE: 30,
    FileStage.CHUNK: 10,
    FileStage.MILVUS_INSERT: 40,
    FileStage.ES_INDEX: 15,
}


class FileProgressTracker:
    def __init__(self, mysql_client=None):
        self.mysql_client = mysql_client

    def _get_stage_order(self) -> List[FileStage]:
        return [
            FileStage.UPLOAD,
            FileStage.PARSE,
            FileStage.CHUNK,
            FileStage.MILVUS_INSERT,
            FileStage.ES_INDEX,
        ]

    def calculate_progress(self, stage_progress: Dict[str, float]) -> int:
        total_progress = 0
        stage_order = self._get_stage_order()

        for stage in stage_order:
            weight = STAGE_WEIGHTS.get(stage, 0)
            progress = stage_progress.get(stage.value, 0)
            total_progress += weight * progress / 100

        return int(total_progress)

    def create_initial_progress(self, file_id: str, file_name: str) -> Dict[str, Any]:
        stage_progress = {}
        stage_details = {}

        for stage in self._get_stage_order():
            stage_progress[stage.value] = 0
            stage_details[stage.value] = {
                "status": FileStageStatus.PENDING.value,
                "start_time": None,
                "end_time": None,
                "duration": None,
            }

        progress_data = {
            "file_id": file_id,
            "file_name": file_name,
            "current_stage": FileStage.UPLOAD.value,
            "overall_progress": 0,
            "stage_progress": stage_progress,
            "stage_details": stage_details,
            "error_code": None,
            "error_message": None,
            "retryable": False,
            "retry_count": 0,
            "last_updated": datetime.now().isoformat(),
        }

        return progress_data

    def update_stage_start(self, progress_data: Dict[str, Any], stage: FileStage) -> Dict[str, Any]:
        stage_value = stage.value

        if stage_value not in progress_data["stage_details"]:
            progress_data["stage_details"][stage_value] = {}

        progress_data["stage_details"][stage_value].update({
            "status": FileStageStatus.RUNNING.value,
            "start_time": datetime.now().isoformat(),
        })

        progress_data["current_stage"] = stage_value
        progress_data["last_updated"] = datetime.now().isoformat()

        insert_logger.info(f"File {progress_data['file_id']} started stage: {stage_value}")

        return progress_data

    def update_stage_progress(self, progress_data: Dict[str, Any], stage: FileStage,
                              stage_progress: float) -> Dict[str, Any]:
        stage_value = stage.value

        progress_data["stage_progress"][stage_value] = min(100, max(0, stage_progress))
        progress_data["overall_progress"] = self.calculate_progress(progress_data["stage_progress"])
        progress_data["last_updated"] = datetime.now().isoformat()

        return progress_data

    def update_stage_success(self, progress_data: Dict[str, Any], stage: FileStage) -> Dict[str, Any]:
        stage_value = stage.value
        now = datetime.now()

        start_time = progress_data["stage_details"][stage_value].get("start_time")
        duration = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                duration = round((now - start_dt).total_seconds(), 2)
            except Exception as e:
                debug_logger.error(f"Error calculating duration: {e}")

        progress_data["stage_details"][stage_value].update({
            "status": FileStageStatus.SUCCESS.value,
            "end_time": now.isoformat(),
            "duration": duration,
        })

        progress_data["stage_progress"][stage_value] = 100
        progress_data["overall_progress"] = self.calculate_progress(progress_data["stage_progress"])
        progress_data["last_updated"] = now.isoformat()

        insert_logger.info(
            f"File {progress_data['file_id']} completed stage: {stage_value}, "
            f"progress: {progress_data['overall_progress']}%"
        )

        return progress_data

    def update_stage_failed(self, progress_data: Dict[str, Any], stage: FileStage,
                            error_code: ErrorCode, error_message: str) -> Dict[str, Any]:
        stage_value = stage.value
        now = datetime.now()

        start_time = progress_data["stage_details"][stage_value].get("start_time")
        duration = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                duration = round((now - start_dt).total_seconds(), 2)
            except Exception as e:
                debug_logger.error(f"Error calculating duration: {e}")

        progress_data["stage_details"][stage_value].update({
            "status": FileStageStatus.FAILED.value,
            "end_time": now.isoformat(),
            "duration": duration,
            "error_code": error_code.value,
            "error_message": error_message,
        })

        progress_data["current_stage"] = FileStage.FAILED.value
        progress_data["error_code"] = error_code.value
        progress_data["error_message"] = error_message
        progress_data["retryable"] = error_code in RETRYABLE_ERRORS
        progress_data["last_updated"] = now.isoformat()

        insert_logger.error(
            f"File {progress_data['file_id']} failed at stage: {stage_value}, "
            f"error_code: {error_code.value}, error: {error_message}"
        )

        return progress_data

    def mark_completed(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        progress_data["current_stage"] = FileStage.COMPLETED.value
        progress_data["overall_progress"] = 100
        progress_data["last_updated"] = datetime.now().isoformat()

        insert_logger.info(f"File {progress_data['file_id']} completed all stages successfully")

        return progress_data

    def start_retry(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        progress_data["retry_count"] = progress_data.get("retry_count", 0) + 1
        progress_data["error_code"] = None
        progress_data["error_message"] = None
        progress_data["retryable"] = False
        progress_data["last_updated"] = datetime.now().isoformat()

        for stage in self._get_stage_order():
            stage_value = stage.value
            if progress_data["stage_details"][stage_value]["status"] == FileStageStatus.FAILED.value:
                progress_data["stage_details"][stage_value] = {
                    "status": FileStageStatus.PENDING.value,
                    "start_time": None,
                    "end_time": None,
                    "duration": None,
                }
                progress_data["stage_progress"][stage_value] = 0

        progress_data["overall_progress"] = self.calculate_progress(progress_data["stage_progress"])

        insert_logger.info(
            f"File {progress_data['file_id']} starting retry attempt {progress_data['retry_count']}"
        )

        return progress_data

    def save_progress(self, file_id: str, progress_data: Dict[str, Any]) -> bool:
        if not self.mysql_client:
            debug_logger.warning("MySQL client not available, cannot save progress")
            return False

        try:
            progress_json = json.dumps(progress_data, ensure_ascii=False)
            self.mysql_client.update_file_progress(file_id, progress_json)
            return True
        except Exception as e:
            debug_logger.error(f"Failed to save progress for file {file_id}: {e}")
            return False

    def load_progress(self, file_id: str) -> Optional[Dict[str, Any]]:
        if not self.mysql_client:
            debug_logger.warning("MySQL client not available, cannot load progress")
            return None

        try:
            progress_json = self.mysql_client.get_file_progress(file_id)
            if progress_json:
                return json.loads(progress_json)
        except Exception as e:
            debug_logger.error(f"Failed to load progress for file {file_id}: {e}")

        return None
