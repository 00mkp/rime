"""Weather-involved share of in-scope US accidents by year around NTSB's 2008 coding change.

Not split by ENSO or hazard, so it is allowed before the pre-registration lock.
"""
import pandas as pd

from rime import paths
from rime.ntsb.classify import category_for, region_for, EXCLUDED_LOCATION
from rime.ntsb.weather_flags import build_flags_from_interim

d = paths.INTERIM / "ntsb"
ev = pd.read_parquet(d / "events.parquet", columns=["ev_id", "ev_year", "ev_type", "ev_country", "ev_state"])
ac = pd.read_parquet(d / "aircraft.parquet", columns=["ev_id", "Aircraft_Key", "acft_category", "far_part", "unmanned"])
en = pd.read_parquet(d / "engines.parquet", columns=["ev_id", "Aircraft_Key", "eng_no", "eng_type"])
en = en.sort_values("eng_no").drop_duplicates(["ev_id", "Aircraft_Key"])
m = ac.merge(en, on=["ev_id", "Aircraft_Key"], how="left").merge(ev, on="ev_id")
m["category"] = [category_for(*r) for r in m[["acft_category", "far_part", "eng_type", "unmanned"]].itertuples(index=False)]
m["region"] = [region_for(c, s) for c, s in zip(m.ev_country, m.ev_state)]
m = m[(m.ev_type == "ACC") & m.category.notna() & (m.region != EXCLUDED_LOCATION)]
m = m.merge(build_flags_from_interim(), on=["ev_id", "Aircraft_Key"])
m = m[m.ev_year.between(2003, 2013)]
share = m.groupby("ev_year")["wx_involved"].agg(["mean", "size"]).rename(columns={"mean": "wx_share", "size": "accidents"})
ratio = share.loc[2008:2010, "wx_share"].mean() / share.loc[2005:2007, "wx_share"].mean()
out = paths.RESULTS / "qa"
out.mkdir(parents=True, exist_ok=True)
share.to_csv(out / "coding_break.csv")
print(share.round(3).to_string())
print(f"ratio mean(2008-10)/mean(2005-07) = {ratio:.3f}")
print("OK: within 0.67-1.5" if 0.67 <= ratio <= 1.5 else "STOP: outside 0.67-1.5 — report to user")
