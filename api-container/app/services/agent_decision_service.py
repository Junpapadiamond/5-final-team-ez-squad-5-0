from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from .agent_activity_service import AgentActivityService
from .agent_action_queue_service import AgentActionQueueService
from .agent_workflow_engine import AgentWorkflowEngine


logger = logging.getLogger(__name__)


class AgentDecisionService:
    """Coordinates activity ingestion with workflow planning."""

    @staticmethod
    def process_pending_events(
        *,
        batch_size: int = 25,
        user_id: Optional[str] = None,
        time_budget_seconds: Optional[float] = None,
    ) -> Dict[str, float]:
        start_time = time.perf_counter()
        events = AgentActivityService.fetch_recent(
            limit=batch_size,
            include_processed=False,
            user_id=user_id,
        )
        generated: int = 0
        processed_ids: List[str] = []

        for event in reversed(events):  # oldest first
            elapsed = time.perf_counter() - start_time
            if time_budget_seconds and elapsed >= time_budget_seconds:
                logger.warning(
                    "AgentDecisionService stopped early for user %s after %.2fs (processed=%s, generated=%s)",
                    user_id or "all",
                    elapsed,
                    len(processed_ids),
                    generated,
                )
                break

            plans = AgentWorkflowEngine.evaluate_event(event)
            if plans:
                AgentActionQueueService.enqueue(plans)
                generated += len(plans)
            processed_ids.append(event.get("_id"))

        if processed_ids:
            AgentActivityService.mark_processed(processed_ids)

        total_elapsed = time.perf_counter() - start_time
        if total_elapsed > 1.5:
            logger.warning(
                "AgentDecisionService.process_pending_events took %.2fs for user %s (processed=%s, generated=%s)",
                total_elapsed,
                user_id or "all",
                len(processed_ids),
                generated,
            )

        return {
            "events_processed": len(processed_ids),
            "plans_generated": generated,
            "duration": round(total_elapsed, 3),
        }
