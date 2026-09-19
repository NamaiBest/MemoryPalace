from .base import GlassesDevice
from .mock import MockGlasses
from .meta_dat import MetaDATGlasses

DEVICES = {"mock": MockGlasses, "meta": MetaDATGlasses}


def make_device(name="mock", **kw) -> GlassesDevice:
    if name not in DEVICES:
        raise ValueError(f"unknown device {name!r}; options: {list(DEVICES)}")
    return DEVICES[name](**kw)
