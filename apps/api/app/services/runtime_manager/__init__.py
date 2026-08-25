"""Optional local AI runtime pack manager.

Manages install/update/repair/remove of versioned runtime packs
(VieNeu worker, Speech worker) in persistent app-data storage.
Core API works without any pack installed.
"""

from app.services.runtime_manager.service import RuntimeManagerService

__all__ = ["RuntimeManagerService"]