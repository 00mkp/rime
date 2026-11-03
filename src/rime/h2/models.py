"""H2a/H3a trend tests and H2b/H3b index-link models (prereg/hypotheses.md §3)."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from rime.h1.models import Effect, fit_nb


def trend_test(years, index, *, one_sided: bool = False) -> Effect:
    """OLS index ~ year with Newey–West (lag 2) SEs. rr/ci hold the slope per decade."""
    y = np.asarray(index, float)
    X = sm.add_constant(np.asarray(years, float))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    b, se = res.params[1], res.bse[1]
    z = b / se
    p = stats.norm.sf(z) if one_sided else 2 * stats.norm.sf(abs(z))
    return Effect(float(10 * b), float(10 * (b - 1.96 * se)), float(10 * (b + 1.96 * se)),
                  float(p), len(y), "ok", "ols_hac")


def _frame(counts: pd.Series, index: pd.Series, hours: pd.Series, break_2008: bool) -> pd.DataFrame:
    d = pd.DataFrame({"count": counts, "index": index, "hours": hours}).dropna()
    d["z"] = (d["index"] - d["index"].mean()) / d["index"].std()
    d["yc"] = d.index - d.index.to_series().mean()
    if break_2008:
        d["post2008"] = (d.index >= 2008).astype(float)
    return d


def link_model(counts: pd.Series, index: pd.Series, hours: pd.Series, *, break_2008: bool):
    d = _frame(counts, index, hours, break_2008)
    formula = "count ~ z + yc + I(yc**2)" + (" + post2008" if break_2008 else "")
    return fit_nb(formula, d, offset=np.log(d["hours"]))


def link_test(counts: pd.Series, index: pd.Series, hours: pd.Series, *, break_2008: bool) -> Effect:
    """NB GLM count ~ z(index) + yc + yc² (+ post2008), offset log(hours); one-sided, rr per 1 SD."""
    n = int(counts.sum())
    res = link_model(counts, index, hours, break_2008=break_2008) if n > 0 else None
    if res is None:
        return Effect(np.nan, np.nan, np.nan, 1.0, n, "not_estimable", "none")
    b, se = res.params["z"], res.bse["z"]
    return Effect(float(np.exp(b)), float(np.exp(b - 1.96 * se)), float(np.exp(b + 1.96 * se)),
                  float(stats.norm.sf(b / se)), n, "ok", res.rime_model)
