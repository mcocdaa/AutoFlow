from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union

@dataclass
class SetupConfig:
    name: str = "unknown"
    scan_subdirs: bool = True
    strategies: Dict[str, str] = field(default_factory=dict)
    scripts: Dict[str, List[str]] = field(default_factory=dict)
    system: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        # Handle simple system list of strings -> list of dicts
        system_raw = data.get("system", [])
        system_processed = []
        for item in system_raw:
            if isinstance(item, str):
                system_processed.append({"name": item, "scope": "all"})
            elif isinstance(item, dict):
                system_processed.append(item)

        # Handle scripts being a list or dict
        scripts_raw = data.get("scripts", {})
        scripts_processed = {}
        if isinstance(scripts_raw, list):
             # Legacy support or simple list -> treat as 'install'
             scripts_processed["install"] = scripts_raw
        elif isinstance(scripts_raw, dict):
             scripts_processed = scripts_raw

        return cls(
            name=data.get("name", "unknown"),
            scan_subdirs=data.get("scan_subdirs", True),
            strategies=data.get("strategies", {}),
            scripts=scripts_processed,
            system=system_processed
        )
