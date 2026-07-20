from chaos_monkey.faults.statistical_drift import StatisticalDrift
from chaos_monkey.faults.enum_drift import EnumDrift
from chaos_monkey.faults.unit_shift import UnitShift
from chaos_monkey.faults.fanout import Fanout
from chaos_monkey.faults.referential import Referential
from chaos_monkey.faults.type_coercion import TypeCoercion

REGISTRY = {
    f.name: f
    for f in [
        StatisticalDrift(),
        EnumDrift(),
        UnitShift(),
        Fanout(),
        Referential(),
        TypeCoercion(),
    ]
}


def get_fault(name):
    if name not in REGISTRY:
        raise ValueError(f"unknown fault: {name}. Available: {list(REGISTRY)}")
    return REGISTRY[name]


def applicable_faults(column_type: str = "any"):
    """Faults whose applies_to matches the column's type family."""
    if column_type == "any":
        return list(REGISTRY)
    return [
        name
        for name, f in REGISTRY.items()
        if "any" in f.applies_to or column_type in f.applies_to
    ]
