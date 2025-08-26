from openhands.core.runtime.tool import ToolExecutor

from .bash_session import BashSession
from .definition import ExecuteBashAction, ExecuteBashObservation


class BashExecutor(ToolExecutor):
    def __init__(
        self,
        working_dir: str,
        username: str | None = None,
    ):
        self.session = BashSession(working_dir, username=username)
        self.session.initialize()

    def __call__(self, action: ExecuteBashAction) -> ExecuteBashObservation:
        return self.session.execute(action)
