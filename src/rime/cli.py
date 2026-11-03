"""`rime <step>` — pipeline steps registered by modules; `rime all` runs them in order."""
import argparse
from collections.abc import Callable

_STEPS: dict[str, tuple[Callable[[], None], str]] = {}


def register(name: str, func: Callable[[], None], help: str) -> None:
    _STEPS[name] = (func, help)


def _load_steps() -> None:
    """Import modules that register steps. Order of imports = order of `all`."""
    import importlib

    for mod in ("rime.ntsb.ingest", "rime.enso", "rime.ntsb.events", "rime.qa", "rime.hazards.classes", "rime.power",
                "rime.h1.run"):
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            if not (e.name and mod.startswith(e.name)):
                raise  # a real missing dependency, not an unbuilt step


def main(argv: list[str] | None = None) -> int:
    _load_steps()
    parser = argparse.ArgumentParser(prog="rime", description=__doc__)
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("all", help="run every step in order")
    for name, (_, help_) in _STEPS.items():
        sub.add_parser(name, help=help_)
    args = parser.parse_args(argv)
    steps = list(_STEPS) if args.step == "all" else [args.step]
    for name in steps:
        print(f"== rime {name}")
        _STEPS[name][0]()
    return 0
