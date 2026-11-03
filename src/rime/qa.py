"""Data-quality report: drops, missing coordinates, and pre-prereg counts by category-year."""
import pandas as pd

from rime import paths
from rime.cli import register
from rime.ntsb.events import counts_by_category_year


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def render_qa(events: pd.DataFrame, drops: dict[str, int]) -> str:
    missing = (events.groupby("year")["dec_latitude"].apply(lambda s: f"{s.isna().mean():.1%}")
               .rename("missing_coords").reset_index())
    counts = counts_by_category_year(events)
    wide = counts.pivot(index="year", columns="category", values="accidents").fillna(0).astype(int).reset_index()
    return "\n\n".join([
        "# rime data-quality report",
        "In-scope = US, 1990+, aircraft categories from the spec. One row per aircraft involvement.",
        "## Rows dropped (aircraft involvements)",
        _md_table(pd.DataFrame(list(drops.items()), columns=["reason", "rows"])),
        "## Missing coordinates (share of in-scope rows without dec_latitude)",
        _md_table(missing),
        "## Accident counts by category and year",
        _md_table(wide),
        "## Weather-involved and fatal counts (long form)",
        _md_table(counts),
    ]) + "\n"


def qa_report() -> None:
    events = pd.read_parquet(paths.PROCESSED / "events_aircraft.parquet")
    drops = pd.read_csv(paths.PROCESSED / "events_drops.csv", index_col=0).iloc[:, 0].to_dict()
    out = paths.RESULTS / "qa"
    out.mkdir(parents=True, exist_ok=True)
    (out / "data_quality.md").write_text(render_qa(events, drops))
    print(f"  wrote {out / 'data_quality.md'}")


register("qa", qa_report, "write the data-quality report")
