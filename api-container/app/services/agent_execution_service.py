from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .agent_action_queue_service import AgentActionQueueService
from .agent_audit_service import AgentAuditService
from .calendar_service import CalendarService
from .messages_service import MessagesService
from .agent_orchestrator import AgentOrchestrator
from .agent_llm_client import AgentLLMClient


logger = logging.getLogger(__name__)


class AgentExecutionService:
    """Executes approved agent actions and records audit trails."""

    @staticmethod
    def execute_action(
        *,
        user_id: str,
        action_id: str,
        execution_payload: Optional[Dict[str, Any]] = None,
        auto_approved: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        action = AgentActionQueueService.get_action(action_id)
        if not action or action.get("user_id") != user_id:
            return None, "Action not found"

        if action.get("status") != "pending":
            return None, "Action already processed"

        action_type = action.get("action_type")
        payload = action.get("payload") or {}
        execution_payload = execution_payload or {}
        metadata: Dict[str, Any] = {
            "auto_approved": auto_approved,
            "executed_at": datetime.utcnow().isoformat() + "Z",
        }

        if action_type in {"collect_style_samples", "prompt_first_message"}:
            AgentActionQueueService.update_status([action_id], status="acknowledged", metadata=metadata)
            AgentAuditService.log(
                user_id=user_id,
                action_id=action_id,
                action_type=action_type,
                status="acknowledged",
                metadata=metadata,
            )
            return {"status": "acknowledged"}, None

        if action_type in {"send_daily_question_reminder", "draft_partner_reply", "send_quiz_followup"}:
            message = execution_payload.get("message") or payload.get("suggested_message")
            if not message:
                if action_type == "send_daily_question_reminder":
                    question = payload.get("question") or "today's reflection"
                    message = f"Quick reminder to answer {question}. Share your thoughts when you can!"
                elif action_type == "send_quiz_followup":
                    score = payload.get("score")
                    message = (
                        f"Loved your quiz score of {score}%! Plan something fun to celebrate together?"
                        if score is not None
                        else "Great job finishing the quiz together! Celebrate with a thoughtful note."
                    )
                else:
                    last_message = (payload.get("last_message") or {}).get("content")
                    if last_message:
                        message = f"Replying to: {last_message}\n\nAppreciate their note and invite a follow-up."
                    else:
                        message = "Send a warm reply to keep the conversation going."

            refined_message, llm_metadata = AgentExecutionService._refine_message(user_id, message)
            result, error = MessagesService.send_message(user_id, refined_message)
            status = "executed" if not error else "failed"
            AgentActionQueueService.update_status(
                [action_id],
                status=status,
                metadata={
                    **metadata,
                    "result": result,
                    "error": error,
                    "llm_metadata": llm_metadata,
                    "refined_message_preview": refined_message[:200],
                },
            )
            AgentAuditService.log(
                user_id=user_id,
                action_id=action_id,
                action_type=action_type,
                status=status,
                metadata={
                    **metadata,
                    "message_preview": refined_message[:160],
                    "llm_metadata": llm_metadata,
                },
            )
            return result, error

        if action_type == "suggest_calendar_event":
            desired = execution_payload or payload
            title = desired.get("title") or "Shared time together"
            date = desired.get("date")
            time_str = desired.get("time")
            if not date or not time_str:
                return None, "date and time are required"
            result, error = CalendarService.create_event(
                user_id,
                title=title,
                date_str=date,
                time_str=time_str,
                description=desired.get("description", "Added by the Together agent"),
            )
            status = "executed" if not error else "failed"
            AgentActionQueueService.update_status([action_id], status=status, metadata={**metadata, "result": result, "error": error})
            AgentAuditService.log(
                user_id=user_id,
                action_id=action_id,
                action_type=action_type,
                status=status,
                metadata={**metadata, "date": date, "time": time_str},
            )
            return result, error

        return None, f"Unsupported action type: {action_type}"

    @staticmethod
    def _refine_message(user_id: str, message: str) -> Tuple[str, Dict[str, Any]]:
        start = time.perf_counter()
        context = AgentOrchestrator.build_context(user_id)
        llm_payload = AgentLLMClient.analyze_tone(message, context)
        duration = time.perf_counter() - start

        metadata: Dict[str, Any] = {
            "duration_seconds": round(duration, 3),
            "refined": False,
        }

        if duration > 3:
            logger.warning(
                "AgentExecutionService LLM refinement slow for user %s (%.2fs)",
                user_id,
                duration,
            )

        if not llm_payload:
            return message, metadata

        refined = llm_payload.get("suggested_reply") or message
        metadata.update(
            {
                "refined": refined != message,
                "model": llm_payload.get("model"),
                "sentiment": llm_payload.get("sentiment"),
                "confidence": llm_payload.get("confidence"),
                "tone_summary": llm_payload.get("tone_summary"),
            }
        )
        return refined, metadata
