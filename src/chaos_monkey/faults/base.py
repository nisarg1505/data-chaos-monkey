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
    applies_to: set[str]

    @abstractmethod
    def apply(self, con, table, column, severity): ...

    @abstractmethod
    def suggested_test(self, column): ...
