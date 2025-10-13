from __future__ import annotations

from typing import Dict, List

from .agent_activity_service import AgentActivityService
from .agent_action_queue_service import AgentActionQueueService
from .agent_workflow_engine import AgentWorkflowEngine


class AgentDecisionService:
    """Coordinates activity ingestion with workflow planning."""

    @staticmethod
    def process_pending_events(batch_size: int = 25) -> Dict[str, int]:
        events = AgentActivityService.fetch_recent(limit=batch_size, include_processed=False)
        generated: int = 0
        processed_ids: List[str] = []

        for event in reversed(events):  # oldest first
            plans = AgentWorkflowEngine.evaluate_event(event)
            if plans:
                AgentActionQueueService.enqueue(plans)
                generated += len(plans)
            processed_ids.append(event.get("_id"))

        if processed_ids:
            AgentActivityService.mark_processed(processed_ids)

        return {"events_processed": len(processed_ids), "plans_generated": generated}
