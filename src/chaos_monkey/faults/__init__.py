from chaos_monkey.faults.statistical_drift import StatisticalDrift
from chaos_monkey.faults.enum_drift import EnumDrift

REGISTRY = {f.name: f for f in [StatisticalDrift(), EnumDrift()]}


def get_fault(name):
    if name not in REGISTRY:
        raise ValueError(f"unknown fault: {name}. Available: {list(REGISTRY)}")
    return REGISTRY[name]
