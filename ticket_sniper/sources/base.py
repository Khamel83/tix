from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseSourceAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: pass

    @abstractmethod
    def parse_inventory(self, raw_body: str, source_event_id: str) -> Tuple[List[Dict[str, Any]], int, bool]: pass
