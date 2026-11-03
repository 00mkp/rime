"""`rime <step>` — pipeline steps registered by modules; `rime all` runs them in order."""
import argparse
from collections.abc import Callable

_STEPS: dict[str, tuple[Callable[..., None], str, bool, Callable | None]] = {}


def register(name: str, func: Callable[..., None], help: str, *, in_all: bool = True,
             configure: Callable | None = None) -> None:
    """in_all=False keeps a step out of `rime all` (e.g. downloads needing the user's account).

    `configure(parser)` adds step options; parsed options are passed to func as keywords.
    """
    _STEPS[name] = (func, help, in_all, configure)


def all_steps() -> list[str]:
    return [n for n, (_, _, in_all, _) in _STEPS.items() if in_all]


def _load_steps() -> None:
    """Import modules that register steps. Order of imports = order of `all`."""
    import importlib

    for mod in ("rime.ntsb.ingest", "rime.enso", "rime.ntsb.events", "rime.qa", "rime.hazards.classes", "rime.power", "rime.era5.process",
                "rime.h2.run",
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
    for name, (_, help_, _, configure) in _STEPS.items():
        p = sub.add_parser(name, help=help_)
        if configure:
            configure(p)
    args = parser.parse_args(argv)
    steps = all_steps() if args.step == "all" else [args.step]
    for name in steps:
        print(f"== rime {name}")
        func, _, _, configure = _STEPS[name]
        if configure and args.step == name:
            func(**{k: v for k, v in vars(args).items() if k != "step"})
        else:
            func()
    return 0
