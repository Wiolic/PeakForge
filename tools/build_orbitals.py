"""Build src/peakforge/data/orbitals.json — core-level table for every element Li–U.

For each element: the main XPS line(s) and common secondary lines with
  be     typical binding energy (eV) of the lower-BE (high-j) component, element or common state
  split  spin–orbit splitting (eV); None for s levels
Area ratio of the doublet follows from l (p 1:2, d 2:3, f 3:4).
'complex' marks levels dominated by multiplet / shake-up structure (open 3d/4d/4f shells):
  the generic model then starts with free singlets instead of a rigid doublet.
Values are approximate handbook values (±0.5 eV typical) — they only seed fits and region
recognition; spin–orbit splittings are kept fixed by default but can be freed in the GUI.
H and He have no practical XPS core level and are not listed.

Run:  python tools/build_orbitals.py
"""
import json
import os

# symbol: [(orbital, be, split, flags)]   flags: 'c' = complex multiplet structure
T = {
    "Li": [("1s", 54.7, None)],
    "Be": [("1s", 111.8, None)],
    "B": [("1s", 188.0, None)],
    "C": [("1s", 284.8, None)],
    "N": [("1s", 399.8, None)],
    "O": [("1s", 531.0, None), ("2s", 23.0, None)],
    "F": [("1s", 685.0, None), ("2s", 30.0, None)],
    "Ne": [("1s", 863.1, None)],
    "Na": [("1s", 1071.8, None), ("2s", 63.6, None), ("2p", 30.8, 0.17)],
    "Mg": [("1s", 1303.0, None), ("2p", 49.8, 0.28), ("2s", 88.6, None)],
    "Al": [("2p", 72.9, 0.44), ("2s", 117.9, None)],
    "Si": [("2p", 99.4, 0.61), ("2s", 150.5, None)],
    "P": [("2p", 130.0, 0.84), ("2s", 189.0, None)],
    "S": [("2p", 164.0, 1.18), ("2s", 228.0, None)],
    "Cl": [("2p", 199.0, 1.60), ("2s", 270.0, None)],
    "Ar": [("2p", 241.9, 2.15)],
    "K": [("2p", 293.0, 2.80), ("2s", 377.1, None), ("3p", 18.0, 0.25), ("3s", 33.6, None)],
    "Ca": [("2p", 347.0, 3.55), ("2s", 438.4, None), ("3p", 25.4, 0.3)],
    "Sc": [("2p", 398.5, 4.90), ("3p", 28.5, 0.4)],
    "Ti": [("2p", 453.9, 6.10), ("3p", 32.6, 0.5)],
    "V": [("2p", 512.2, 7.60), ("3p", 37.2, 0.6)],
    "Cr": [("2p", 574.2, 9.30, "c"), ("3p", 42.2, 0.8)],
    "Mn": [("2p", 638.7, 11.20, "c"), ("3p", 47.4, 1.0), ("3s", 82.0, None, "c")],
    "Fe": [("2p", 706.7, 13.10, "c"), ("3p", 52.9, 1.2)],
    "Co": [("2p", 778.1, 15.00, "c"), ("3p", 59.3, 1.5)],
    "Ni": [("2p", 852.6, 17.30, "c"), ("3p", 66.2, 1.8)],
    "Cu": [("2p", 932.6, 19.80), ("3p", 75.1, 2.4), ("3s", 122.5, None)],
    "Zn": [("2p", 1021.8, 23.10), ("3p", 88.6, 2.8), ("3d", 10.1, 0.5)],
    "Ga": [("2p", 1116.5, 26.90), ("3d", 18.7, 0.45), ("3p", 104.0, 3.3)],
    "Ge": [("3d", 29.3, 0.58), ("2p", 1217.0, 31.10), ("3p", 121.0, 4.0)],
    "As": [("3d", 41.7, 0.69), ("3p", 140.5, 4.9)],
    "Se": [("3d", 55.5, 0.86), ("3p", 160.0, 5.7)],
    "Br": [("3d", 69.0, 1.05), ("3p", 182.0, 6.9)],
    "Kr": [("3d", 93.8, 1.20)],
    "Rb": [("3d", 111.5, 1.50), ("3p", 238.0, 9.0)],
    "Sr": [("3d", 133.5, 1.79), ("3p", 268.5, 10.0)],
    "Y": [("3d", 155.8, 2.05), ("3p", 299.5, 12.0)],
    "Zr": [("3d", 178.9, 2.43), ("3p", 330.5, 13.6)],
    "Nb": [("3d", 202.3, 2.72), ("3p", 360.6, 15.3)],
    "Mo": [("3d", 227.9, 3.13), ("3p", 394.0, 17.5)],
    "Tc": [("3d", 253.9, 3.40)],
    "Ru": [("3d", 280.1, 4.17), ("3p", 461.4, 22.2)],
    "Rh": [("3d", 307.2, 4.74), ("3p", 496.5, 25.0)],
    "Pd": [("3d", 335.1, 5.26), ("3p", 532.4, 27.9)],
    "Ag": [("3d", 368.2, 6.00), ("3p", 573.0, 30.0)],
    "Cd": [("3d", 405.0, 6.74), ("4d", 10.7, 0.7)],
    "In": [("3d", 443.9, 7.54), ("4d", 16.9, 0.86)],
    "Sn": [("3d", 484.9, 8.41), ("4d", 24.0, 1.05)],
    "Sb": [("3d", 528.2, 9.34), ("4d", 32.1, 1.25)],
    "Te": [("3d", 573.0, 10.40), ("4d", 40.5, 1.5)],
    "I": [("3d", 619.3, 11.50), ("4d", 49.2, 1.7)],
    "Xe": [("3d", 669.7, 12.60), ("4d", 63.9, 2.0)],
    "Cs": [("3d", 726.0, 13.90), ("4d", 75.5, 2.3)],
    "Ba": [("3d", 780.6, 15.30), ("4d", 90.0, 2.6)],
    "La": [("3d", 835.8, 16.80, "c"), ("4d", 102.0, 2.9, "c")],
    "Ce": [("3d", 882.0, 18.60, "c"), ("4d", 109.0, 3.2, "c")],
    "Pr": [("3d", 932.0, 20.40, "c"), ("4d", 114.0, 3.5, "c")],
    "Nd": [("3d", 980.8, 22.40, "c"), ("4d", 120.5, 3.8, "c")],
    "Pm": [("3d", 1026.0, 24.20, "c"), ("4d", 125.0, 4.0, "c")],
    "Sm": [("3d", 1081.0, 27.00, "c"), ("4d", 129.0, 4.3, "c")],
    "Eu": [("3d", 1125.0, 29.70, "c"), ("4d", 128.0, 4.6, "c")],
    "Gd": [("4d", 140.4, 5.0, "c"), ("3d", 1186.0, 32.0, "c")],
    "Tb": [("4d", 146.0, 5.3, "c"), ("3d", 1241.0, 35.0, "c")],
    "Dy": [("4d", 152.4, 5.6, "c"), ("3d", 1296.0, 37.5, "c")],
    "Ho": [("4d", 160.0, 6.0, "c")],
    "Er": [("4d", 168.4, 6.3, "c")],
    "Tm": [("4d", 175.5, 6.6, "c")],
    "Yb": [("4d", 185.0, 7.0, "c"), ("4f", 7.0, 1.3, "c")],
    "Lu": [("4f", 7.1, 1.50), ("4d", 196.0, 10.0)],
    "Hf": [("4f", 14.3, 1.66), ("4d", 212.0, 10.5)],
    "Ta": [("4f", 21.9, 1.91), ("4d", 226.0, 11.7)],
    "W": [("4f", 31.4, 2.18), ("4d", 243.5, 12.4)],
    "Re": [("4f", 40.3, 2.43), ("4d", 260.0, 13.6)],
    "Os": [("4f", 50.7, 2.71), ("4d", 279.0, 14.0)],
    "Ir": [("4f", 60.9, 2.98), ("4d", 296.3, 15.0)],
    "Pt": [("4f", 71.1, 3.33), ("4d", 314.6, 16.8)],
    "Au": [("4f", 84.0, 3.67), ("4d", 335.1, 17.9)],
    "Hg": [("4f", 99.9, 4.05), ("4d", 358.8, 19.4)],
    "Tl": [("4f", 117.7, 4.42), ("5d", 12.5, 2.2)],
    "Pb": [("4f", 136.9, 4.86), ("5d", 18.0, 2.6)],
    "Bi": [("4f", 156.9, 5.31), ("5d", 24.4, 3.0)],
    "Po": [("4f", 176.5, 5.80)],
    "At": [("4f", 195.0, 6.30)],
    "Rn": [("4f", 214.0, 6.80)],
    "Fr": [("4f", 234.0, 7.30)],
    "Ra": [("4f", 254.0, 7.90)],
    "Ac": [("4f", 272.0, 8.40)],
    "Th": [("4f", 333.1, 9.30)],
    "Pa": [("4f", 360.0, 10.10)],
    "U": [("4f", 377.3, 10.90, "c")],
}
Z = {s: i for i, s in enumerate(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
    "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
    "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U".split(), start=1)}

# approximate Scofield cross-sections (Al Kα, C 1s = 1, whole subshell) — rough quantification only
RSF = {"C 1s": 1.00, "N 1s": 1.80, "O 1s": 2.93, "F 1s": 4.43, "Na 1s": 8.52, "Al 2p": 0.537, "Si 2p": 0.817,
       "P 2p": 1.19, "S 2p": 1.68, "Cl 2p": 2.29, "K 2p": 3.97, "Ca 2p": 5.07, "Ti 2p": 7.81, "Cr 2p": 11.7,
       "Mn 2p": 13.9, "Fe 2p": 16.4, "Co 2p": 19.2, "Ni 2p": 22.2, "Cu 2p": 25.4, "Zn 2p": 28.8, "Mo 3d": 9.50,
       "Ag 3d": 18.0, "W 4f": 9.80, "Pt 4f": 15.9, "Au 4f": 17.1}
SUB = {"p": ("1/2", "3/2"), "d": ("3/2", "5/2"), "f": ("5/2", "7/2")}
RATIO = {"p": 0.5, "d": 2 / 3, "f": 0.75}

out = {}
for el, lines in T.items():
    for item in lines:
        orb, be, split = item[:3]
        flags = item[3] if len(item) > 3 else ""
        l = orb[-1]
        key = f"{el} {orb}"
        d = dict(z=Z[el], element=el, level=orb, be=be, rsf=RSF.get(key))
        if l == "s" or split is None:
            d.update(split=None, ratio=None, sub=None)
        else:
            lo, hi = SUB[l]
            d.update(split=split, ratio=round(RATIO[l], 4),
                     sub=[f"{orb}{hi}", f"{orb}{lo}"])      # main (high-j, lower BE) first
        if "c" in flags:
            d["complex"] = True
        d["main"] = lines[0][0] == orb
        out[key] = d

doc = {"_note": ("Core levels for every element Li–U (H, He: no practical XPS core level). be: typical BE (eV) of "
                 "the main (high-j, lower-BE) component; split: spin–orbit splitting (eV); ratio: area of the "
                 "low-j partner / main; complex: multiplet/shake-up dominated, generic model uses free singlets. "
                 "Approximate handbook values — seeds for fitting, not reference data. rsf: approximate Scofield "
                 "cross-sections (Al Kα, C 1s = 1) for rough quantification only — use your instrument's RSFs."),
       "orbitals": dict(sorted(out.items(), key=lambda kv: (kv[1]["z"], -kv[1]["main"], kv[1]["be"])))}
dst = os.path.join(os.path.dirname(__file__), "..", "src", "peakforge", "data", "orbitals.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
print(f"{len(out)} core levels, {len(T)} elements -> {os.path.abspath(dst)}")
