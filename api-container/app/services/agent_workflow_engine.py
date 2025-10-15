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
    title: Optional[str]
    summary: Optional[str]
    confidence: float
    requires_approval: bool
    payload: Dict[str, Any]
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    rationale: Optional[str] = None
    ai_source: str = "legacy"
    llm_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "workflow": self.workflow,
            "trigger_event_id": self.trigger_event_id,
            "action_type": self.action_type,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "payload": self.payload,
            "context_snapshot": self.context_snapshot,
            "generated_at": self.generated_at,
            "rationale": self.rationale,
            "ai_source": self.ai_source,
            "llm_metadata": self.llm_metadata,
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
        context = AgentOrchestrator.build_context(user_id)
        insights = cls._retrieve_insights(user_id, event)
        if insights:
            context["insights"] = insights

        plans = cls._generate_llm_plans(
            user_id=user_id,
            event=event,
            scenario=scenario,
            context=context,
        )

        if not plans:
            handler_name = cls.WORKFLOW_HANDLERS.get(scenario)
            if not handler_name:
                return []
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
    def _coerce_action_type(action: Dict[str, Any], fallback: str) -> str:
        value = action.get("action_type")
        if isinstance(value, str) and value.strip():
            return value.strip()
        title = action.get("title")
        if isinstance(title, str) and title.strip():
            slug = title.lower().strip().replace(" ", "_")
            return slug or fallback
        return fallback

    @staticmethod
    def _coerce_confidence(action: Dict[str, Any], default: float = 0.6) -> float:
        value = action.get("confidence")
        if isinstance(value, (int, float)):
            try:
                num = float(value)
                if num < 0:
                    return 0.0
                if num > 1:
                    return 1.0
                return num
            except (TypeError, ValueError):
                return default
        return default

    @classmethod
    def _generate_llm_plans(
        cls,
        *,
        user_id: str,
        event: Dict[str, Any],
        scenario: str,
        context: Dict[str, Any],
    ) -> List[AgentActionPlan]:
        package = AgentOrchestrator.plan_actions(user_id, event, base_context=context)
        if not package:
            return []
        raw_actions = package.get("actions") or []
        if not isinstance(raw_actions, list) or not raw_actions:
            return []

        metadata = {
            "model": package.get("model"),
            "strategy": package.get("strategy") or package.get("plan"),
            "explanation": package.get("explanation"),
        }

        plans: List[AgentActionPlan] = []
        for index, raw_action in enumerate(raw_actions):
            if not isinstance(raw_action, dict):
                continue
            action_type = cls._coerce_action_type(raw_action, fallback=f"{scenario}_followup")
            title = raw_action.get("title")
            summary = raw_action.get("summary")
            if not title and isinstance(summary, str):
                title = summary[:60]
            if not summary and isinstance(title, str):
                summary = title

            payload: Dict[str, Any] = {}
            for key in ("call_to_action", "suggested_message", "notes", "follow_up_question"):
                value = raw_action.get(key)
                if isinstance(value, (str, int, float)) and str(value).strip():
                    payload[key] = str(value).strip()

            payload["source_event_id"] = event.get("_id")

            llm_metadata = {
                **metadata,
                "action_index": index,
                "raw_action": raw_action,
            }

            plans.append(
                cls._new_plan(
                    user_id=user_id,
                    workflow=scenario,
                    trigger_event_id=event.get("_id"),
                    action_type=action_type,
                    title=title,
                    summary=summary,
                    confidence=cls._coerce_confidence(raw_action),
                    requires_approval=bool(raw_action.get("requires_approval", True)),
                    payload=payload,
                    context=context,
                    rationale=raw_action.get("rationale") or raw_action.get("reason"),
                    ai_source="openai",
                    llm_metadata=llm_metadata,
                )
            )

        return plans

    @staticmethod
    def _new_plan(
        *,
        user_id: str,
        workflow: str,
        trigger_event_id: Optional[str],
        action_type: str,
        title: Optional[str],
        summary: Optional[str],
        confidence: float,
        requires_approval: bool,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        rationale: Optional[str] = None,
        ai_source: str = "legacy",
        llm_metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentActionPlan:
        context_snapshot = {
            "partner_status": context.get("partner_status"),
            "daily_question": context.get("daily_question"),
            "recent_messages": context.get("recent_messages", [])[:3],
            "upcoming_events": context.get("upcoming_events", [])[:3],
            "style_profile": (context.get("style_profile") or {}).get("style_summary"),
            "insights": context.get("insights"),
        }
        if llm_metadata:
            context_snapshot["llm_model"] = llm_metadata.get("model")
            context_snapshot["llm_strategy"] = llm_metadata.get("strategy")
        return AgentActionPlan(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workflow=workflow,
            trigger_event_id=trigger_event_id,
            action_type=action_type,
            title=title,
            summary=summary,
            confidence=confidence,
            requires_approval=requires_approval,
            payload=payload,
            context_snapshot=context_snapshot,
            rationale=rationale,
            ai_source=ai_source,
            llm_metadata=llm_metadata or {},
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
                    title="Teach your tone",
                    summary="Share a handful of favourite messages so the agent understands your style.",
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
                    title="Send a welcome note",
                    summary="Kick off the experience by sending your partner a quick hello.",
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
                    title="Nudge today’s reflection",
                    summary="Remind yourself (and your partner) to answer the daily question.",
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
                    title="Draft a reply",
                    summary="Reply warmly to keep the conversation moving.",
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
            title="Celebrate your quiz win",
            summary="Send a congratulatory note about the compatibility quiz.",
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
            title="Plan a shared moment",
            summary="Find time together in the coming week.",
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
