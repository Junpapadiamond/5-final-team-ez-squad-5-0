from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .agent_orchestrator import AgentOrchestrator


@dataclass
class AgentActionPlan:
    id: str
    user_id: str
    workflow: str
    trigger_event_id: Optional[str]
    action_type: str
    confidence: float
    requires_approval: bool
    payload: Dict[str, Any]
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "workflow": self.workflow,
            "trigger_event_id": self.trigger_event_id,
            "action_type": self.action_type,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "payload": self.payload,
            "context_snapshot": self.context_snapshot,
            "generated_at": self.generated_at,
            "rationale": self.rationale,
        }


class AgentWorkflowEngine:
    """State-machine style evaluator that turns activity feed events into action plans."""

    WORKFLOW_HANDLERS = {
        "onboarding": "_handle_onboarding",
        "daily_check_in": "_handle_daily_check_in",
        "quiz_follow_up": "_handle_quiz_follow_up",
        "anniversary_planning": "_handle_anniversary_planning",
    }

    @classmethod
    def evaluate_event(cls, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        user_id = event.get("user_id")
        if not user_id:
            return []

        scenario = event.get("scenario") or cls._infer_scenario(event)
        handler_name = cls.WORKFLOW_HANDLERS.get(scenario)
        if not handler_name:
            return []

        context = AgentOrchestrator.build_context(user_id)
        insights = cls._retrieve_insights(user_id, event)
        if insights:
            context["insights"] = insights

        handler = getattr(cls, handler_name)
        plans = handler(user_id=user_id, event=event, context=context)
        return [plan.to_dict() for plan in plans]

    @staticmethod
    def _infer_scenario(event: Dict[str, Any]) -> str:
        mapping = {
            "daily_question_missed": "daily_check_in",
            "message_received": "daily_check_in",
            "quiz_completed": "quiz_follow_up",
            "calendar_gap_detected": "anniversary_planning",
        }
        return mapping.get(event.get("event_type"), "daily_check_in")

    @staticmethod
    def _retrieve_insights(user_id: str, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Optional hook for the upcoming RAG service; safe no-op when disabled."""
        base_url = os.environ.get("AGENT_INSIGHTS_URL")
        if not base_url:
            return None

        try:
            response = requests.post(
                base_url,
                json={
                    "user_id": user_id,
                    "question": event.get("event_type"),
                    "scope": event.get("scenario"),
                },
                timeout=float(os.environ.get("AGENT_INSIGHTS_TIMEOUT", "3.0")),
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
        except Exception:
            return None
        return None

    @staticmethod
    def _new_plan(
        *,
        user_id: str,
        workflow: str,
        trigger_event_id: Optional[str],
        action_type: str,
        confidence: float,
        requires_approval: bool,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        rationale: Optional[str] = None,
    ) -> AgentActionPlan:
        context_snapshot = {
            "partner_status": context.get("partner_status"),
            "daily_question": context.get("daily_question"),
            "recent_messages": context.get("recent_messages", [])[:3],
            "upcoming_events": context.get("upcoming_events", [])[:3],
            "style_profile": (context.get("style_profile") or {}).get("style_summary"),
            "insights": context.get("insights"),
        }
        return AgentActionPlan(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workflow=workflow,
            trigger_event_id=trigger_event_id,
            action_type=action_type,
            confidence=confidence,
            requires_approval=requires_approval,
            payload=payload,
            context_snapshot=context_snapshot,
            rationale=rationale,
        )

    @classmethod
    def _handle_onboarding(
        cls,
        *,
        user_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[AgentActionPlan]:
        plans: List[AgentActionPlan] = []
        style_profile = context.get("style_profile") or {}
        has_messages = bool(context.get("recent_messages"))

        if not style_profile.get("message_count"):
            plans.append(
                cls._new_plan(
                    user_id=user_id,
                    workflow="onboarding",
                    trigger_event_id=event.get("_id"),
                    action_type="collect_style_samples",
                    confidence=0.6,
                    requires_approval=False,
                    payload={
                        "prompt": "Share 3 messages you like so the agent can learn your tone.",
                    },
                    context=context,
                    rationale="New user without style profile",
                )
            )

        if not has_messages:
            plans.append(
                cls._new_plan(
                    user_id=user_id,
                    workflow="onboarding",
                    trigger_event_id=event.get("_id"),
                    action_type="prompt_first_message",
                    confidence=0.5,
                    requires_approval=False,
                    payload={
                        "message": "Send your partner a quick hello to get started.",
                    },
                    context=context,
                    rationale="Kickstart engagement",
                )
            )

        return plans

    @classmethod
    def _handle_daily_check_in(
        cls,
        *,
        user_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[AgentActionPlan]:
        plans: List[AgentActionPlan] = []
        event_type = event.get("event_type")

        if event_type == "daily_question_missed":
            question = (context.get("daily_question") or {}).get("question")
            plans.append(
                cls._new_plan(
                    user_id=user_id,
                    workflow="daily_check_in",
                    trigger_event_id=event.get("_id"),
                    action_type="send_daily_question_reminder",
                    confidence=0.75,
                    requires_approval=True,
                    payload={
                        "question": question,
                    },
                    context=context,
                    rationale="Reminder for missed daily reflection",
                )
            )

        if event_type == "message_received":
            recent = context.get("recent_messages") or []
            latest = recent[0] if recent else {}
            plans.append(
                cls._new_plan(
                    user_id=user_id,
                    workflow="daily_check_in",
                    trigger_event_id=event.get("_id"),
                    action_type="draft_partner_reply",
                    confidence=0.65,
                    requires_approval=True,
                    payload={
                        "last_message": latest,
                    },
                    context=context,
                    rationale="Partner reached out recently",
                )
            )

        return plans

    @classmethod
    def _handle_quiz_follow_up(
        cls,
        *,
        user_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[AgentActionPlan]:
        summary = (event.get("payload") or {}).get("score")
        rationale = "Follow up on completed compatibility session"
        message = "Celebrate your match score together!"
        if summary is not None:
            message = f"Celebrate your {summary}% compatibility score together!"
        plan = cls._new_plan(
            user_id=user_id,
            workflow="quiz_follow_up",
            trigger_event_id=event.get("_id"),
            action_type="send_quiz_followup",
            confidence=0.7,
            requires_approval=True,
            payload={
                "score": summary,
                "suggested_message": message,
            },
            context=context,
            rationale=rationale,
        )
        return [plan]

    @classmethod
    def _handle_anniversary_planning(
        cls,
        *,
        user_id: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[AgentActionPlan]:
        window = event.get("payload", {})
        plan = cls._new_plan(
            user_id=user_id,
            workflow="anniversary_planning",
            trigger_event_id=event.get("_id"),
            action_type="suggest_calendar_event",
            confidence=0.6,
            requires_approval=True,
            payload={
                "suggested_window": window,
                "idea": "Schedule a shared activity for the coming week.",
            },
            context=context,
            rationale="Detected gap in upcoming shared plans",
        )
        return [plan]
