from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import traceback

from qanything_kernel.utils.file_process_state import ProcessStage, FileProcessContext, STAGE_ORDER
from qanything_kernel.utils.custom_log import insert_logger, debug_logger


class RollbackAction(str, Enum):
    CLEAN_MILVUS = "clean_milvus"
    CLEAN_ES = "clean_es"
    CLEAN_MYSQL_CHUNKS = "clean_mysql_chunks"
    CLEAN_LOCAL_CACHE = "clean_local_cache"
    RESET_CHUNKS_COUNT = "reset_chunks_count"


class StageRollbackContract:
    def __init__(self, stage: ProcessStage):
        self.stage = stage
        self.actions: List[RollbackAction] = []

    def add_action(self, action: RollbackAction) -> "StageRollbackContract":
        if action not in self.actions:
            self.actions.append(action)
        return self

    def __repr__(self) -> str:
        return f"StageRollbackContract(stage={self.stage.value}, actions={[a.value for a in self.actions]})"


STAGE_ROLLBACK_CONTRACTS: Dict[ProcessStage, StageRollbackContract] = {}


def _build_rollback_contracts():
    upload_contract = StageRollbackContract(ProcessStage.UPLOAD)
    upload_contract.add_action(RollbackAction.CLEAN_LOCAL_CACHE)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.UPLOAD] = upload_contract

    parse_contract = StageRollbackContract(ProcessStage.PARSE)
    parse_contract.add_action(RollbackAction.CLEAN_LOCAL_CACHE)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.PARSE] = parse_contract

    split_contract = StageRollbackContract(ProcessStage.SPLIT)
    split_contract.add_action(RollbackAction.CLEAN_LOCAL_CACHE)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.SPLIT] = split_contract

    embed_contract = StageRollbackContract(ProcessStage.EMBED)
    embed_contract.add_action(RollbackAction.CLEAN_MILVUS)
    embed_contract.add_action(RollbackAction.CLEAN_ES)
    embed_contract.add_action(RollbackAction.RESET_CHUNKS_COUNT)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.EMBED] = embed_contract

    index_contract = StageRollbackContract(ProcessStage.INDEX)
    index_contract.add_action(RollbackAction.CLEAN_MILVUS)
    index_contract.add_action(RollbackAction.CLEAN_ES)
    index_contract.add_action(RollbackAction.RESET_CHUNKS_COUNT)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.INDEX] = index_contract

    complete_contract = StageRollbackContract(ProcessStage.COMPLETE)
    complete_contract.add_action(RollbackAction.CLEAN_MILVUS)
    complete_contract.add_action(RollbackAction.CLEAN_ES)
    complete_contract.add_action(RollbackAction.CLEAN_MYSQL_CHUNKS)
    complete_contract.add_action(RollbackAction.RESET_CHUNKS_COUNT)
    complete_contract.add_action(RollbackAction.CLEAN_LOCAL_CACHE)
    STAGE_ROLLBACK_CONTRACTS[ProcessStage.COMPLETE] = complete_contract


_build_rollback_contracts()


def get_rollback_contracts_for_stage(from_stage: ProcessStage) -> List[StageRollbackContract]:
    try:
        from_idx = STAGE_ORDER.index(from_stage)
    except ValueError:
        return []

    contracts = []
    for i in range(len(STAGE_ORDER) - 1, from_idx - 1, -1):
        stage = STAGE_ORDER[i]
        if stage in STAGE_ROLLBACK_CONTRACTS:
            contracts.append(STAGE_ROLLBACK_CONTRACTS[stage])
    return contracts


class StageRollbackResult:
    def __init__(self, file_id: str):
        self.file_id = file_id
        self.success_actions: Dict[RollbackAction, bool] = {}
        self.errors: Dict[RollbackAction, str] = {}

    def record_success(self, action: RollbackAction):
        self.success_actions[action] = True

    def record_error(self, action: RollbackAction, error: str):
        self.errors[action] = error

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "success_actions": [k.value for k in self.success_actions.keys()],
            "errors": {k.value: v for k, v in self.errors.items()},
            "has_errors": self.has_errors,
        }


class StageRollbackHandler:
    def __init__(self, milvus_client=None, es_client=None, mysql_client=None):
        self.milvus_client = milvus_client
        self.es_client = es_client
        self.mysql_client = mysql_client

    def _execute_action(
        self,
        action: RollbackAction,
        file_id: str,
        context: Optional[FileProcessContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        extra = extra or {}
        try:
            if action == RollbackAction.CLEAN_MILVUS:
                return self._clean_milvus(file_id, extra)
            elif action == RollbackAction.CLEAN_ES:
                return self._clean_es(file_id, extra)
            elif action == RollbackAction.CLEAN_MYSQL_CHUNKS:
                return self._clean_mysql_chunks(file_id, extra)
            elif action == RollbackAction.RESET_CHUNKS_COUNT:
                return self._reset_chunks_count(file_id, extra)
            elif action == RollbackAction.CLEAN_LOCAL_CACHE:
                return self._clean_local_cache(file_id, context, extra)
            else:
                debug_logger.warning(f"Unknown rollback action: {action.value} for file {file_id}")
                return False
        except Exception as e:
            debug_logger.warning(
                f"Rollback action {action.value} failed for {file_id}: {e}\n{traceback.format_exc()}"
            )
            return False

    def _clean_milvus(self, file_id: str, extra: Dict[str, Any]) -> bool:
        if not self.milvus_client:
            return False
        try:
            expr = f'file_id == "{file_id}"'
            self.milvus_client.delete_expr(expr)
            insert_logger.info(f"Rollback: cleaned milvus for {file_id}")
            return True
        except Exception as e:
            debug_logger.warning(f"Rollback clean_milvus failed for {file_id}: {e}")
            return False

    def _clean_es(self, file_id: str, extra: Dict[str, Any]) -> bool:
        if not self.es_client:
            return False
        try:
            if hasattr(self.es_client, "delete_files"):
                file_chunks = extra.get("file_chunks") or []
                if not file_chunks and self.mysql_client:
                    file_chunks = self.mysql_client.get_chunk_size([file_id])
                self.es_client.delete_files([file_id], file_chunks)
            elif hasattr(self.es_client, "delete_file"):
                self.es_client.delete_file(file_id)
            else:
                return False
            insert_logger.info(f"Rollback: cleaned es for {file_id}")
            return True
        except Exception as e:
            debug_logger.warning(f"Rollback clean_es failed for {file_id}: {e}")
            return False

    def _clean_mysql_chunks(self, file_id: str, extra: Dict[str, Any]) -> bool:
        if not self.mysql_client:
            return False
        try:
            self.mysql_client.delete_documents([file_id])
            insert_logger.info(f"Rollback: cleaned mysql chunks for {file_id}")
            return True
        except Exception as e:
            debug_logger.warning(f"Rollback clean_mysql_chunks failed for {file_id}: {e}")
            return False

    def _reset_chunks_count(self, file_id: str, extra: Dict[str, Any]) -> bool:
        if not self.mysql_client:
            return False
        try:
            self.mysql_client.update_chunks_number(file_id, 0)
            insert_logger.info(f"Rollback: reset chunks count for {file_id}")
            return True
        except Exception as e:
            debug_logger.warning(f"Rollback reset_chunks_count failed for {file_id}: {e}")
            return False

    def _clean_local_cache(
        self,
        file_id: str,
        context: Optional[FileProcessContext],
        extra: Dict[str, Any],
    ) -> bool:
        import os
        import shutil

        file_location = extra.get("file_location")
        if not file_location and context and context.metadata:
            file_location = context.metadata.get("file_location")
        if not file_location:
            return False

        try:
            file_dir = os.path.dirname(file_location) if file_location else None
            if file_dir and os.path.exists(file_dir) and "upload" in file_dir:
                shutil.rmtree(file_dir, ignore_errors=True)
                insert_logger.info(f"Rollback: cleaned local cache for {file_id}")
                return True
            return False
        except Exception as e:
            debug_logger.warning(f"Rollback clean_local_cache failed for {file_id}: {e}")
            return False

    def rollback_to_stage(
        self,
        file_id: str,
        to_stage: ProcessStage,
        context: Optional[FileProcessContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> StageRollbackResult:
        result = StageRollbackResult(file_id)
        contracts = get_rollback_contracts_for_stage(to_stage)

        insert_logger.info(
            f"Rollback {file_id} to stage {to_stage.value}, "
            f"contracts: {[c.stage.value for c in contracts]}"
        )

        for contract in contracts:
            for action in contract.actions:
                success = self._execute_action(action, file_id, context, extra)
                if success:
                    result.record_success(action)
                else:
                    result.record_error(action, f"{action.value} execution failed")

        insert_logger.info(
            f"Rollback {file_id} completed: success={list(result.success_actions.keys())}, "
            f"errors={list(result.errors.keys())}"
        )
        return result

    def rollback_for_retry(
        self,
        file_id: str,
        context: FileProcessContext,
        extra: Optional[Dict[str, Any]] = None,
    ) -> StageRollbackResult:
        retry_stage = context.get_retry_stage()
        rollback_result = self.rollback_to_stage(file_id, retry_stage, context, extra)
        context.reset_for_retry(rollback_result=rollback_result.to_dict())
        return rollback_result
