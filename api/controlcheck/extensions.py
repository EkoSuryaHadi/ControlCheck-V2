"""Future contracts only: no forecasting or action execution is enabled."""
from dataclasses import dataclass
from typing import Literal, Protocol


class ForecastProvider(Protocol):
    def forecast(self, snapshot_ids: list[str], assumptions: dict, method_version: str) -> dict: ...


@dataclass(frozen=True)
class AgentActionProposal:
    project_id: str
    snapshot_id: str
    action_type: str
    evidence: tuple[dict, ...]
    expected_effect: str
    approval: Literal['pending', 'approved', 'rejected'] = 'pending'


SUPPORTED_IMPORTS = ('.csv', '.xlsx')
PLANNED_IMPORTS = ('.mpp', '.xml', '.xer')
