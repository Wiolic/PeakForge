"""Tabulated curves of a fit — the single source for PNG, Excel, CSV and Origin exports."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..core.fit import FitResult
from ..core.model import RegionModel


def curve_table(model: RegionModel, res: FitResult) -> tuple[pd.DataFrame, list[dict]]:
    """Columns: BE, Measured, Background, Fit envelope, <components (bg + comp)>, Residual.
    Returns (dataframe sorted by descending BE, column meta [{name, long, units, comment}])."""
    o = np.argsort(res.x)[::-1]
    cols = {"BE": res.x[o], "Measured": res.y[o], "Background": res.bg[o], "Fit envelope": res.envelope[o]}
    meta = [dict(name="BE", long="Binding energy", units="eV", comment=""),
            dict(name="Measured", long="Intensity", units="a.u.", comment="Measured"),
            dict(name="Background", long="Intensity", units="a.u.", comment="Background"),
            dict(name="Fit envelope", long="Intensity", units="a.u.", comment="Fit envelope")]
    used = set(cols)
    for c in model.components:
        lines = res.comp_curves[c.name]
        tot = np.sum(lines, axis=0)
        label = c.label or c.name
        nm = label
        while nm in used:
            nm += "_"
        used.add(nm)
        cols[nm] = (res.bg + tot)[o]
        meta.append(dict(name=nm, long="Intensity", units="a.u.", comment=label, component=c.name))
    cols["Residual"] = res.residual[o]
    meta.append(dict(name="Residual", long="Intensity", units="a.u.", comment="Residual"))
    return pd.DataFrame(cols), meta


def component_table(model: RegionModel, res: FitResult, sample: str = "", region: str = "") -> pd.DataFrame:
    rows = []
    for r in res.summary_rows(model):
        rows.append({"Sample": sample, "Region": region, "Component": r["label"],
                     "Shape": r["shape"], "Center (eV)": r["center"], "± center": r["center_err"],
                     "FWHM (eV)": r["fwhm"], "± FWHM": r["fwhm_err"],
                     "Partner (eV)": r.get("center2"), "Split (eV)": r.get("split"),
                     "Area": r["area"], "± area": r["area_err"],
                     "Fraction (%)": r["fraction"], "± fraction": r.get("fraction_err"),
                     "Apparent FWHM (eV)": r.get("fwhm_apparent")})
    df = pd.DataFrame(rows)
    df.attrs.update(rms=res.rms_pct, chi2=res.chi2_red, bic=res.bic, noise=res.noise)
    return df
