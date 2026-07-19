"""The Fault contract every corruption implements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FaultResult:
    table: str
    column: str
    description: str
    rows_affected: int


class Fault(ABC):
    name: str
    applies_to: set[str]  # column types this fault is valid for

    @abstractmethod
    def apply(self, con, table: str, column: str, severity: float) -> FaultResult:
        """Mutate ONLY the given table/column in the connected (cloned) db."""
        ...

    @abstractmethod
    def suggested_test(self, column: str) -> str:
        """The dbt test that WOULD catch this fault."""
        ...
