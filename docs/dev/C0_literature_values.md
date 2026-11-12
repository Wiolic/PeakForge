# C0 文献数值表 / C0 literature values (F1–F6)

状态 / Status: 仅文献检索，未改代码；**待 Opus 复核后才能进入代码或 METHODS**。
Research only, no code changed; **values must be reviewed by Opus before entering code or METHODS**.
检索日期 / Retrieved: 2026-11-12.

## 0. 读表说明 / How to read this file

**可信度标记 / Evidence labels**

| 标记 / Label | 含义 / Meaning |
|---|---|
| **A** | 数值由本次检索直接从原文 PDF 文本或数据库记录读出 / read directly from the paper's PDF text or a database record in this session |
| **B** | 数值来自二手页面（厂商参考页、博客、他文转述）/ read from a secondary page (vendor reference page, blog, another paper quoting it) |
| **C** | 由 A 级数值算出（给出算式）/ computed here from A-level numbers (formula given) |
| **unverified** | 未能从来源核实，不得写入代码 / could not be confirmed from a source; must not enter code |

**能量标尺 / Energy scale.** 俄歇线换算 / Auger lines are converted with `BE = hν − KE`, `hν(Al Kα) = 1486.6 eV`.

**参考能量不同 / Reference scales differ.** Biesinger 2011：外来碳 C 1s = 284.8 eV，金属用 Au 4f7/2 = 83.95 eV。Friedman 2018（Nafion）：HOPG sp² C 1s = 284.4 eV。Beamson & Briggs：饱和烃 C 1s = 285.00 eV。NIST 记录各不相同。跨来源比较的不确定度不小于 ±0.2 eV。
Biesinger 2011 uses adventitious C 1s = 284.8 eV (metals: Au 4f7/2 = 83.95 eV); Friedman 2018 uses HOPG at 284.4 eV; Beamson & Briggs use hydrocarbon C 1s = 285.00 eV; NIST records vary. Cross-source comparison is no better than ±0.2 eV.

**光源 / Photon source.** 每行都注明。Pfeifer 2016、Martin 2020、McLellan 2023 是同步辐射，不是 Al Kα，线宽与卫星相对强度不能直接照搬。
Stated per row. Pfeifer 2016, Martin 2020 and McLellan 2023 are synchrotron work, not Al Kα; widths and satellite intensities do not transfer directly.

---

## F1 — Ir 4d5/2；K 2p；含氟聚合物 C 1s / F 1s

结论 / Bottom line: Ir 4d5/2：金属 296.2–296.3 eV（宽 4.2 eV），无水 IrO₂ 298.1 eV（宽 5.0 eV），水合 IrO₂ 298.6 eV（宽 4.6 eV），均为单色 Al Kα。K 2p 劈裂 2.7–2.8 eV 有出处；**KOH 没有查到记录**。Nafion 的 CF₂ = 292.2 eV、F 1s = 689.7 eV 有出处。
Ir 4d5/2: metal 296.2–296.3 eV (FWHM 4.2 eV), anhydrous IrO₂ 298.1 eV (5.0 eV), hydrated IrO₂ 298.6 eV (4.6 eV), all with monochromatic Al Kα. K 2p splitting 2.7–2.8 eV is sourced; **no KOH record found**. Nafion CF₂ = 292.2 eV and F 1s = 689.7 eV are sourced.

### F1a Ir 4d

| Quantity | Value (eV) | Range / uncertainty | Material | Source (hν) | Citation | Label |
|---|---|---|---|---|---|---|
| Ir 4d5/2 BE | 296.30 | not given in record | Ir metal | non-monochromated; anode not stated in record; Au-calibrated | NIST SRD 20 record 30574 = Nyholm, Berndtsson, Mårtensson, J. Phys. C 13, L1091 (1980), DOI 10.1088/0022-3719/13/36/009 | A |
| Ir 4d5/2 BE | 296.3 | — | Ir (elemental table) | compilation | X-ray Data Booklet Table 1-1 (N5) | A |
| Ir 4d3/2 BE | 311.9 | — | Ir (elemental table) | compilation | X-ray Data Booklet Table 1-1 (N4) | A |
| Ir 4d splitting | 15.60 | — | Ir metal | — | NIST SRD 20 record 33877 (DS-4d) | A |
| Ir 4d5/2 BE | 297.1–298.5 | 6 records | IrClₓ, IrCl₄·xH₂O, an Ir(IV) chloride complex | — | NIST SRD 20 records 41722, 41695, 41692, 41687, 92756, 92762 | A |
| Ir 4d5/2 BE; FWHM | 296.2; 4.20 | FWHM ±0.2 | Ir foil, Ar⁺-sputtered | monochromatic Al Kα, 20 eV pass energy; Au 4f7/2 = 83.95 | Freakley, Ruiz-Esquius, Morgan, Surf. Interface Anal. 49, 794 (2017), Table 2 | A |
| Ir 4d5/2 BE; FWHM | 298.1; 4.96 | FWHM ±0.2 | IrO₂ anhydrous (rutile) | monochromatic Al Kα, 20 eV pass energy; C 1s = 284.8 where neutralised | Freakley et al. 2017, Table 2 | A |
| Ir 4d5/2 BE; FWHM | 298.6; 4.64 | FWHM ±0.2 | IrO₂ hydrated (amorphous) | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d5/2 BE; FWHM | 298.1; 3.92 / 297.8; 3.92 | FWHM ±0.2 | IrCl₃ hydrated / anhydrous | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d3/2 BE; FWHM | 312.1; 4.29 / 313.9; 5.24 / 314.4; 5.00 | FWHM ±0.2 | Ir / IrO₂ anhydrous / IrO₂ hydrated | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d splitting | 15.9 (Ir), 15.8 (oxides, chlorides) | — | as above | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d5/2 : 4d3/2 area | 60.1 : 39.9 (60.2 : 39.8 for anhydrous IrO₂) | — | as above | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d5/2 line shape | GL(70), "fit 4d5/2 only" (Ir, both IrO₂); LF(1.2, 0.7, 25, 280) (IrCl₃) | — | as above | same | Freakley et al. 2017, Table 2 | A |
| Ir 4d5/2 mean BE from NIST | 296.3 (Ir), 297.8 ± 0.6 (IrClₓ), N/A (IrO₂) | — | compilation | — | Freakley et al. 2017, Table 1 | A |
| σ(Ir 4d5/2)/σ(C 1s) | 11.0 | — | free atom, 1.5 keV | calc. | Scofield 1973 via Kalha et al. digitisation; 146250 / 13291 | C |

备注 / Notes
- NIST 中 Ir 只有金属和氯化物的 4d5/2 记录，没有氧化物记录；氧化物的数值来自 Freakley 2017：IrO₂ 的 4d5/2 比金属高 1.9 eV（无水）到 2.4 eV（水合）。
  NIST holds 4d5/2 records only for the metal and chlorides; the oxide values come from Freakley 2017: IrO₂ 4d5/2 lies 1.9 eV (anhydrous) to 2.4 eV (hydrated) above the metal.
- Ir 4d5/2 很宽（4.2–5.0 eV），是 C 1s 组分宽度的数倍。Freakley 建议只拟合 4d5/2，因为把 4d3/2 一起放进 Shirley 背景时两峰之间的背景定义不好。
  Ir 4d5/2 is broad (4.2–5.0 eV), several times a C 1s component. Freakley advises fitting 4d5/2 only, because a Shirley background spanning 4d3/2 is poorly defined between the peaks.
- C0 实测未校正的 296–297.8 eV 加上约 +1.9 eV 的荷电校正后为 297.9–299.7 eV，与氧化物的 298.1–298.6 eV 相符的是低端；这一比较由 Opus 复核。
  The uncorrected 296–297.8 eV seen in C0 becomes 297.9–299.7 eV after a charge correction of about +1.9 eV; the low end matches the oxide values 298.1–298.6 eV. Opus should review this comparison.
- 单位原子截面 Ir 4d5/2 是 C 1s 的 11 倍，所以少量 Ir 就能在 C 1s 窗口上端压过 C 1s，与 C0 的观察一致。
  Per atom the Ir 4d5/2 cross-section is 11× that of C 1s, so little Ir is enough to dominate the top of the C 1s window, consistent with the C0 observation.

### F1b K 2p

| Quantity | Value (eV) | Material | Source (hν) | Citation | Label |
|---|---|---|---|---|---|
| K 2p3/2 BE | 292.9 | KCl | C 1s = 284.8 | Thermo Fisher XPS reference page, potassium | B |
| K 2p3/2 BE | 293.2 | KBr | C 1s = 284.8 | Thermo Fisher XPS reference page, potassium | B |
| K 2p3/2 BE | 293.00 | KBr | — | NIST SRD 20 record 111090 | A |
| K 2p3/2 BE | 292.50, 292.80, 293.10 | KF | — | NIST SRD 20 records 25898, 25894, 25890 | A |
| K 2p3/2 BE | 292.90 | KNO₃ | — | NIST SRD 20 record 26472 | A |
| K 2p3/2 BE | 292.80 | KI | — | NIST SRD 20 record 26418 | A |
| K 2p3/2 BE | 292.50, 293.30 | K₂SO₄ | — | NIST SRD 20 records 67276, 26737 | A |
| K 2p3/2 BE | 292.80, 293.40 | KClO₄ | — | NIST SRD 20 records 26717, 26719 | A |
| K 2p3/2 BE | 294.70 | K metal | — | NIST SRD 20 record 26413 | A |
| K 2p3/2 / 2p1/2 BE | 294.6 / 297.3 | K (elemental table) | compilation | X-ray Data Booklet Table 1-1 | A |
| K 2p3/2 BE | **unverified** | KOH, K₂CO₃ | — | no record found in the 105 of 135 NIST K 2p3/2 records retrieved | unverified |
| K 2p splitting | 2.70 | K metal | non-monochromated | NIST SRD 20 record 33307 = Petersson & Karlsson, Phys. Scr. 16, 425 (1977), DOI 10.1088/0031-8949/16/5-6/041 | A |
| K 2p splitting | 2.80 | KBr | non-monochromated | NIST SRD 20 record 33320 = Wagner et al., Handbook of XPS, Perkin-Elmer 1979 | A |
| K 2p splitting | 2.8 | KCl ("Δchloride") | — | Thermo Fisher XPS reference page, potassium | B |
| K 2s BE | about 378 | K salts | — | Thermo Fisher XPS reference page, potassium (confirmation line) | B |
| σ(2p3/2)/σ(2p1/2) | 1.946 | free atom, 1.5 keV | calc. | Scofield 1973; 34807 / 17886 | C |

备注 / Notes
- K⁺ 盐的 2p3/2 集中在 292.5–293.4 eV（9 种盐 14 条记录），C0 用的 293.0 与劈裂 2.8 在此范围内。
  K⁺ salts cluster at 292.5–293.4 eV (14 records, 9 salts); the 293.0 and 2.8 used in C0 lie inside this range.
- Thermo 页面指出弱的 K 2p 容易与 CF₂ 的 C 1s 或芳香 π–π* 卫星混淆，建议用 K 2s（约 378 eV）确认。
  The Thermo page warns that weak K 2p is easily confused with CF₂ C 1s or aromatic π–π* satellites and suggests confirming with K 2s near 378 eV.

### F1c 含氟聚合物 / Fluoropolymers

| Quantity | Value (eV) | Material / group | Source (hν), reference | Citation | Label |
|---|---|---|---|---|---|
| C 1s | 292.2 | Nafion, –CF₂–CF₂– backbone (main peak) | focused Al Kα 1486.6 eV, PHI VersaProbe II; HOPG sp² C 1s = 284.4 | Friedman et al., J. Electrochem. Soc. 165, H733 (2018), DOI 10.1149/2.0771811jes; Results text, fits in SI Fig. S3 | A |
| C 1s | about 293.6 | Nafion, –CF₃ (shoulder) | same | same | A |
| C 1s | about 289.9–290 | Nafion, –OCF₂– | same | same | A |
| C 1s | about 287.0 | Nafion, –CF– | same | same | A |
| C 1s | about 285.5 | adventitious carbon on Nafion | same | same | A |
| F 1s | about 689.7 | Nafion (single peak) | same | same | A |
| S 2p | about 170.1 | Nafion sulfonate (single peak) | same | same | A |
| O 1s | 535.5 / 533.1 | Nafion ether / sulfonate | same | same; Fig. 1 caption | A |
| F 1s | 689.67 | PTFE (–CF₂–CF₂–)ₙ | monochromatic Al Kα (Scienta ESCA300); hydrocarbon C 1s = 285.00 | Beamson & Briggs, High Resolution XPS of Organic Polymers, Wiley 1992, as quoted on xpsfitting.com "Fluorine" page | B |
| C 1s | 292.48 | PTFE | same | Beamson & Briggs 1992; **not confirmed in this session** | unverified |
| C 1s | about 292 / about 294 | CF₂ / CF₃ in polymers | C 1s = 284.8 | Thermo Fisher XPS reference page, carbon | B |
| F 1s | 688–689 | organic fluorine | C 1s = 284.8 | Thermo Fisher XPS reference page, fluorine | B |
| F 1s | 684–685.5 | metal fluorides | C 1s = 284.8 | Thermo Fisher XPS reference page, fluorine | B |
| C 1s | 293.23, 294.09 | Fomblin Y perfluoropolyether (which carbon each belongs to was not captured) | Beamson & Briggs | NIST SRD 20 records 23184, 23185 | A |
| C 1s FWHM, F 1s FWHM | **unverified** | Nafion, PTFE | — | not stated in the text retrieved | unverified |

备注 / Notes
- C0 实测校正后的 CF₂ 为 291.6–291.9 eV，比 Friedman 的 292.2 低 0.3–0.6 eV。Friedman 自己指出用 –CF₂/–CF₃ 作参考时结合能的变动约 0.5 eV，而 HOPG 约 0.05 eV。所以 CF₂ 只能作 ±0.5 eV 级别的交叉检验，不能作主参考。
  The corrected CF₂ found in C0 (291.6–291.9 eV) is 0.3–0.6 eV below Friedman's 292.2. Friedman et al. state that referencing to –CF₂/–CF₃ varies by about 0.5 eV against about 0.05 eV for HOPG. CF₂ is usable as a ±0.5 eV cross-check, not as a primary reference.
- Thermo 页面提示含氟聚合物对 X 射线敏感，应先采 C 1s 与 F 1s 再采全谱。
  The Thermo page notes fluoropolymers are X-ray sensitive; C 1s and F 1s should be acquired before the survey.
### F1d 催化层中的 Nafion / Nafion inside a catalyst layer (Dzara et al. 2024)

Source: Dzara, Artyushkova, Foster, Eskandari, Chen, Mauger, Atanassov, Karan, Pylypenko, J. Phys. Chem. C 128, 8467–8482 (2024), DOI 10.1021/acs.jpcc.4c00872 (CC-BY 4.0), read from the publisher PDF. Instruments: Kratos AXIS Supra, PHI VersaProbe III (both monochromatic Al Kα), Scienta-Omicron HiPP-3. Data in this table: multispot protocol. Label **A**.

| Core level | Nafion thin film on glassy carbon (eV) | Pt/HSC catalyst layer with Nafion, no BE correction (eV) | Shift (their Table 3) |
|---|---|---|---|
| C 1s, CFₓ of Nafion | 292.2 (set by calibration; as measured 292.5) | **290.5** | −1.7 eV |
| F 1s | 689.3 | **687.7** | −1.6 eV |
| O 1s, ether | about 536 (film value from section 3.2) | 534.3 | −1.8 eV |
| O 1s, sulfonic acid | 532.5 | 531.7 | −0.7 eV |
| S 2p | not stated numerically | not stated numerically | −0.6 eV |
| C 1s, carbon support | — | 284.2 (verified on the conductive Pt/HSC powder on conducting tape, no referencing) | — |

Statements in the paper (label **A**):
- 催化层中导电的催化剂/载体不需要校正（碳载体在 284.2 eV），而同一张谱里 Nafion 的 CFₓ 与 F 1s 比薄膜低 1.6–1.7 eV。作者的解释是 Nafion 与导体接触后局部电子环境改变（荷电更少或负电荷转移），并说明还需要进一步实验支持。
  In a catalyst layer the conductive catalyst/support needs no correction (carbon support at 284.2 eV), while in the same spectrum Nafion CFₓ and F 1s sit 1.6–1.7 eV lower than in a thin film. The authors attribute this to a changed local electronic environment of Nafion in contact with a conductor (less charging, or negative charge transfer) and say further experiments are needed.
- 各能级位移不相等（−0.6 到 −1.8 eV），PTFE 主链物种位移最大。/ The shifts differ by core level (−0.6 to −1.8 eV), largest for the PTFE-backbone species.
- Nafion 在常规采谱时间内（几十分钟）被 X 射线损伤，磺酸基优先损失（O 1s 533 eV 峰下降多于 536 eV 峰）；开中和枪时损伤更重；催化层中的 Nafion 比薄膜降解更快。
  Nafion is damaged by X-rays within tens of minutes of normal acquisition, losing sulfonic acid preferentially (the O 1s 533 eV peak drops more than the 536 eV peak); charge neutralisation makes it worse; Nafion in an electrode degrades faster than in a thin film.
- 建议的规程：在多个新鲜位置各做短扫描再求和（每点约 21 min，至少 5 点）。他们用的窗口：F 1s 10 eV，S 2p 和 O 1s 12 eV，C 1s 15 eV，步长 0.1 eV。
  Recommended protocol: short scans on several fresh spots, then summed (about 21 min per spot, at least 5 spots). Their windows: F 1s 10 eV, S 2p and O 1s 12 eV, C 1s 15 eV, 0.1 eV step.
- 薄膜谱的标定是把 C 1s 设为 292.2 eV（引 Friedman 2018）。/ Thin-film spectra were calibrated by setting C 1s to 292.2 eV (citing Friedman 2018).

**与 C0 实测的对应 / Match with the C0 observations.** C0 报告未校正的 CF₂ 在 290.1–290.5 eV、F 1s 在 686–688 eV，与 Dzara 催化层的 290.5 / 687.7 eV 一致，而后者是在**催化剂不需要校正**的谱上测到的。用户确认样品是催化剂与 Nafion 配成 ink 喷在膜上（见 F6），属于同一类样品。因此：
The C0 report has uncorrected CF₂ at 290.1–290.5 eV and F 1s at 686–688 eV, the same as Dzara's catalyst-layer values 290.5 / 687.7 eV, which were measured on spectra where **the catalyst needed no correction**. The user confirms the samples are catalyst + Nafion ink sprayed on membrane (see F6), the same kind of sample. Therefore:
- 催化层里 Nafion 的 CF₂ 位置（约 290.5 eV）不等于膜或薄膜的 292.2 eV；**不能用 292.2 eV 去标定催化层谱**，否则催化剂线会被多抬约 1.7 eV。
  The CF₂ position of Nafion in a catalyst layer (about 290.5 eV) is not the membrane or thin-film 292.2 eV; **292.2 eV must not be used to calibrate catalyst-layer spectra**, or catalyst lines are raised by about 1.7 eV too much.
- 催化剂线与离聚物线可以处在不同的电位上，一个偏移量不能同时校正两者。这一点需要 Opus 结合 C0 的 "+1.9 eV 偏移自洽" 结论重新审视：C–C、晶格 O、Ir 4f 互相自洽，而 CF₂ 校正后落在 291.6–291.9 而不是 292.2 eV，与本表的图像相符。
  Catalyst lines and ionomer lines can sit at different potentials; one offset cannot correct both. Opus should revisit the C0 conclusion "a +1.9 eV offset is self-consistent" in this light: C–C, lattice O and Ir 4f agree with each other, while the corrected CF₂ lands at 291.6–291.9 instead of 292.2 eV, consistent with this picture.

---

## F2 — Co LMM 与 F KLL 在 Al Kα 结合能标尺上的位置 / Co LMM and F KLL on the Al Kα BE scale

结论 / Bottom line: 最强的 Co L₃VV 在 713–717 eV，远离 Co 2p 窗口。**但 Biesinger 在 Co 金属谱中报道了一个 766.2 eV、宽 2.2 eV 的 LMM 俄歇峰**，就在 770–815 eV 窗口下沿外 3.8 eV。F KLL 主峰在 827–835 eV，**没有进入 815 eV 以下**。
The strongest Co L₃VV lies at 713–717 eV, far from the Co 2p window. **Biesinger reports an LMM Auger peak at 766.2 eV (FWHM 2.2 eV) in Co metal**, 3.8 eV below the 770–815 eV window. The F KLL main line is at 827–835 eV and **does not reach below 815 eV**.

| Line | KE (eV) | BE on Al Kα scale (eV) | Material | Citation | Label |
|---|---|---|---|---|---|
| Co L₃VV | 773.00, 773.20, 773.40 | 713.6, 713.4, 713.2 | Co metal | NIST SRD 20 records 32895, 32894, R-70 | A (KE), C (BE) |
| Co L₃VV | 773.60 | 713.0 | Co₃O₄ | NIST SRD 20 record 32905 | A, C |
| Co L₃VV | 769.40 | 717.2 | CoO | NIST SRD 20 record 32906 | A, C |
| Co LMM | — | 713 | Co (used to tell Co 2p from Ba 3d) | Thermo Fisher XPS reference page, cobalt | B |
| Co "LMM B" Auger | 720.4 (C) | **766.2**, FWHM 2.2 | Co metal, monochromatic Al Kα, Kratos Axis Ultra | Biesinger et al. 2011, Table 5 footnote b | A |
| Co LMM (weaker lines) | — | "overlaps Co 2p region" (no number) | Co | Thermo Fisher XPS reference page, cobalt | B |
| Co LMM near 766 eV in oxides / hydroxides | **unverified** | **unverified** | CoO, Co₃O₄, Co(OH)₂, CoOOH | not found | unverified |
| F KL₂₃L₂₃(¹D) | 652.40 | 834.2 | "CF₂" (fluoropolymer) | NIST SRD 20 record 32361 = Wagner, in Briggs (ed.), Handbook of X-ray and Ultraviolet Photoelectron Spectroscopy, 1977 | A, C |
| F KL₂₃L₂₃(¹D) | 651.7–659.3 | 827.3–834.9 | 40 metal fluorides (AlF₃ lowest KE, AgF highest) | NIST SRD 20, F Auger query, 56 records | A, C |
| F KL₁L₂₃ | 627.40 | 859.2 | LiF | NIST SRD 20 record 111669 | A, C |
| F KL₁L₁ | 608.00 | 878.6 | LiF | NIST SRD 20 record 111670 | A, C |
| F KLL | — | 832 and 858 | fluorine compounds | Thermo Fisher XPS reference page, fluorine | B |
| F KLL line width / low-BE onset | **unverified** | **unverified** | — | not found | unverified |

备注 / Notes
- 766.2 eV 这个峰的跃迁归属（我推测是 L₃M₂₃M₄₅）**未核实**；Biesinger 只写 "LMM B"。
  The transition assignment of the 766.2 eV peak (my guess: L₃M₂₃M₄₅) is **unverified**; Biesinger only writes "LMM B".
- 俄歇峰在结合能标尺上随荷电同样平移。未校正谱若被中和枪压低 1–2 eV，这个峰仍在 770 eV 以下；它的高 BE 侧尾部是否进入窗口取决于背景，文献未给。
  On the BE scale an Auger peak shifts with charging like a photoelectron peak. With spectra pushed 1–2 eV low by the flood gun it stays below 770 eV; whether its high-BE tail enters the window is not documented.
- 一个本机 Co 2p 谱在 815 eV 处的最大值：以上数据不支持把它归为 F KLL 峰（最低的 F KLL 在 827 eV）。其他解释这里没有出处，不下结论。
  The maximum at 815 eV in one local Co 2p scan is not supported as an F KLL peak by these data (lowest F KLL at 827 eV). No sourced alternative is offered here.
- Thermo 页面另提示 Ba 3d 与 Co 2p 强重叠，可用 Co LMM（713 eV）或 Ba 4d（85 eV）区分。
  The Thermo page also flags strong Ba 3d / Co 2p overlap, resolvable with Co LMM (713 eV) or Ba 4d (85 eV).

---

## F3 — Co 2p 多重态 / 卫星拟合参数 / Co 2p multiplet and satellite parameters

结论 / Bottom line: Biesinger 2011 表 5 已完整取得。**这套参数只针对 2p3/2**，原文没有给 2p1/2 各组分的参数。2p 劈裂：金属 14.96–15.10，Co³⁺/Co₃O₄ 14.9–15.3，高自旋 Co²⁺ 15.5–16.2 eV。
Biesinger 2011 Table 5 was obtained in full. **The parameters cover 2p3/2 only**; the paper gives no component parameters for 2p1/2. 2p splitting: metal 14.96–15.10, Co³⁺/Co₃O₄ 14.9–15.3, high-spin Co²⁺ 15.5–16.2 eV.

### F3a 采集与拟合条件 / Acquisition and fitting conditions (Biesinger 2011, section 2)

| Item | Value | Label |
|---|---|---|
| Instrument, source | Kratos Axis Ultra, monochromatic Al Kα (15 mA, 14 kV) | A |
| Pass energy | 10 eV or 20 eV; Ag 3d5/2 FWHM 0.47 eV and 0.55 eV respectively | A |
| Energy calibration | Au 4f7/2 = 83.95 eV; Cu 2p3/2 = 932.63 eV | A |
| Charge reference | adventitious C 1s (C–C, C–H) = 284.8 eV; stated error ±0.1–0.2 eV; metals referenced to Au 4f7/2 = 83.95 eV | A |
| Background | standard Shirley; for Co with metal present, an offset of the high-BE endpoint is needed because oxide 2p3/2 satellites overlap the metal 2p1/2 at 793.1 eV | A |
| Component line shape | GL(30) for broad or satellite-bearing species (Co(OH)₂ named as an example) | A |
| Co metal main peak | asymmetric LA(1.2,5,5) (CasaXPS) | A |
| Co metal plasmons | +3.0 eV (surface) and +5.0 eV (bulk), FWHM 3.0 eV each; after Grosvenor et al., Inorg. Chem. 44, 8988 (2005) | A |
| Co metal 2p1/2 | 793.1 eV (so 2p splitting = 15.0 eV with 778.1) | A |
| CoOOH | fitted to a digitised spectrum of Yang, Liu, Martens, Frost, J. Phys. Chem. C 114, 111 (2010); 20 eV pass energy column only | A |

### F3b 表 5 / Table 5 — Co 2p3/2

Source: Biesinger, Payne, Grosvenor, Lau, Gerson, Smart, Appl. Surf. Sci. 257, 2717–2730 (2011), Table 5 (p. 2726). Monochromatic Al Kα. BE in eV; Δ = separation from the previous peak; FWHM at 10 eV / 20 eV pass energy. Label **A**.

| Compound | Peak | BE (eV) | Δ to previous (eV) | Area (%) | FWHM 10 eV PE | FWHM 20 eV PE |
|---|---|---|---|---|---|---|
| Co(0) | 1 (asymmetric) | 778.1 | — | 81.0 | 0.70 | 0.75 |
| Co(0) | 2 (surface plasmon) | 781.1 | 3.00 | 11.0 | 3.00 | 3.00 |
| Co(0) | 3 (bulk plasmon) | 783.1 | 2.00 | 8.0 | 3.00 | 3.00 |
| CoO | 1 | 780.0 | — | 46.6 | 2.23 | 2.24 |
| CoO | 2 | 782.1 | 2.10 | 25.7 | 2.59 | 2.66 |
| CoO | 3 | 785.5 | 3.40 | 1.6 | 2.42 | 2.29 |
| CoO | 4 | 786.5 | 1.00 | 26.1 | 5.28 | 4.98 |
| Co(OH)₂ | 1 | 780.4 | — | 38.1 | 2.01 | 2.04 |
| Co(OH)₂ | 2 | 782.2 | 1.80 | 26.6 | 2.60 | 2.55 |
| Co(OH)₂ | 3 | 786.0 | 3.79 | 33.0 | 4.47 | 4.47 |
| Co(OH)₂ | 4 | 790.4 | 4.40 | 2.4 | 2.33 | 2.33 |
| CoOOH | 1 | 780.1 | — | 61.4 | — | 1.48 |
| CoOOH | 2 | 781.4 | 1.32 | 24.5 | — | 1.48 |
| CoOOH | 3 | 783.1 | 1.68 | 5.2 | — | 1.48 |
| CoOOH | 4 | 790.1 | 7.07 | 8.9 | — | 3.30 |
| Co₃O₄ | 1 | 779.6 | — | 40.5 | 1.38 | 1.39 |
| Co₃O₄ | 2 | 780.9 | 1.30 | 29.1 | 1.55 | 1.62 |
| Co₃O₄ | 3 | 782.2 | 1.30 | 15.2 | 1.94 | 2.18 |
| Co₃O₄ | 4 | 785.2 | 3.00 | 8.1 | 4.28 | 4.44 |
| Co₃O₄ | 5 | 789.5 | 4.30 | 7.2 | 3.15 | 3.29 |

表注（原文）/ Table footnotes (as printed): (a) 结合能有效到 0.1 eV，间距多给一位 / BEs are significant to 0.1 eV, separations carry one more figure; (b) Co(0) 峰 1 的非对称线型与宽度由标准 Co 金属样品定义 LA(1.2,5,5)，另见 766.2 eV 处 LMM B 俄歇峰（宽 2.2 eV）/ Co(0) peak 1 shape and width defined by the standard metal sample, LA(1.2,5,5); LMM B Auger peak at 766.2 eV, 2.2 eV FWHM; (c) CoOOH 来自数字化谱的拟合 / CoOOH from a fit of a digitised spectrum.

**Opus 复核（2026-11-13）/ Opus review:** 全表逐格与两个来源核对一致：期刊 PDF 文本（第 2726 页，按列）以及作者本人网站 xpsfitting.com “Cobalt” 页的表图。唯一差别：CoO 峰 4 面积期刊为 26.1，网站图为 26（四舍五入）；以期刊 26.1 为准。
Every cell checked against both the journal PDF text (p. 2726, by column) and the author's own reproduction on xpsfitting.com ("Cobalt" post, table image). Only difference: CoO peak 4 area is 26.1 in the journal and 26 in the web image (rounded); the journal value 26.1 stands.

**转录核对 / Transcription check.** PDF 文本抽取时该表各行上下错位，我按列重排。核对：每个化合物面积合计 100.0 或 100.1 %；每个 Δ 与相邻 BE 之差一致（例：Co₃O₄ 782.2 + 3.00 = 785.2，785.2 + 4.30 = 789.5；CoOOH 783.1 + 7.07 = 790.17）。**请 Opus 对照原文 PDF 第 2726 页再核一次。**
The PDF text extraction shifted the rows of this table vertically; I re-assembled them by column. Checks: areas sum to 100.0 or 100.1 % per compound, and every Δ matches the BE differences. **Opus should re-check against p. 2726 of the PDF.**

### F3c Co 2p 自旋轨道劈裂 / Co 2p spin–orbit splitting (2p1/2 − 2p3/2)

Source: NIST SRD 20, data type "Doublet Separation" (DS-2p), 50 Co records retrieved. These are separations of peak maxima, mostly from non-monochromated sources. Label **A** unless noted.

| Species | Splitting (eV) | Records | Notes / primary citation where captured |
|---|---|---|---|
| Co metal | 14.96, 15.05, 15.10 | 33246, 33252, 33238 | 33246 = Lebugle, Axelsson, Nyholm, Mårtensson, Phys. Scr. 23, 825 (1981); 33252 = PHI Handbook 1979 |
| Co metal | 14.99 | — | Thermo Fisher reference page ("Δmetal"), label B |
| Co metal | 15.0 | — | Biesinger 2011 text: 2p1/2 at 793.1 vs 2p3/2 at 778.1, label C |
| Co metal | 15.1 | — | X-ray Data Booklet Table 1-1: 793.2 − 778.1, label C |
| CoO | 15.10, 15.30, 15.50, 15.80, 15.90, 16.00 | 33417, 33420, 33413, 33421, 33419, 33414 | 33413 = PHI Handbook 1979; spread 0.9 eV |
| Co(OH)₂ | 16.00 (three records) | 33287, 33288, 33289 | 33287 = Frost, McDowell, Woolsey, Chem. Phys. Lett. 17, 320 (1972) |
| CoOOH | 15.00 | 33303 | Schenck, Dillard, Murray, J. Colloid Interface Sci. 95, 398 (1983) |
| Co₃O₄ | 14.90, 15.00, 15.00, 15.10, 15.30 | 33392, 33394, 33408, 33395, 33406 | 33392 = Chuang, Brundle, Rice, Surf. Sci. 59, 413 (1976) |
| Co²⁺ halides, sulfate, acetate | 15.7–16.2 | 33225, 33230, 33240, 33241, 33245, 33258, 33259, 33277, 33403, 33409, 33304 | CoCl₂ 16.0/16.1, CoBr₂ 15.7/15.8, CoI₂ 16.0, CoF₂ 16.0/16.1, CoSO₄ 15.9/16.2 |
| Co²⁺ spinels | 15.7–16.1 | 33377, 33378, 33383, 33388, 33402, 33411 | CoAl₂O₄, CoCr₂O₄, CoMoO₄, CoFe₂O₄, CoMn₂O₄ |
| Co³⁺ low-spin complexes | 14.9–15.1 | 33206, 33215, 33211, 33281, 33285, 33327 | K₃[Co(CN)₆], Co(NH₃)₆Cl₃, Na₃[Co(NO₂)₆] |
| CoF₃ | 16.20 | 33261 | high-spin Co³⁺ outlier |
| ZnCo₂O₄ | 15.10 | 33412 | Co³⁺ spinel |

备注 / Notes
- 现有约束 15.0 ±7 %（13.95–16.05 eV）：Co²⁺ 记录 16.0–16.2 eV 压在或超出上限，C0 "对 Co²⁺ 偏紧" 的判断有数据支持。
  The current constraint 15.0 ±7 % (13.95–16.05 eV) puts Co²⁺ records at 16.0–16.2 eV on or beyond the upper limit; the C0 judgement "too tight for Co²⁺" is supported.
- 这些劈裂是包络峰顶之差。多重态拟合中每个组分是否用同一劈裂，文献没有给出；Biesinger 的做法是只拟合 2p3/2。
  These are separations of envelope maxima. Whether each multiplet component shares one splitting is not given in the literature; Biesinger fits 2p3/2 only.
- Scofield 的 2p3/2 : 2p1/2 截面比为 1.930（1.5 keV，167890 / 86993），不是 2.000。标签 C。
  Scofield's 2p3/2 : 2p1/2 cross-section ratio is 1.930 (1.5 keV), not 2.000. Label C.
- Thermo 页面：Co(II) 的卫星约在 786 eV；Co₃O₄ 是 Co(II)/Co(III) 混合，两类卫星都有；氧化物易被 Ar⁺ 还原。标签 B。
  Thermo page: Co(II) satellite near 786 eV; Co₃O₄ shows features of both states; oxides are easily reduced by Ar⁺. Label B.

---

## F4 — Ta 4f 区域的重叠线 / Lines overlapping the Ta 4f region

结论 / Bottom line: Ta 4f 劈裂 **1.92 eV**（三条 NIST 记录），表值 1.91 没问题，撞下限 1.78 是重叠造成的。Ta₂O₅ 的 Ta 5p3/2 在 **37.3 eV**，金属在 32.7 eV。氧化物 O 2s 在 21–23 eV。氟化物 F 2s 在 28.4–31.8 eV；**含氟聚合物的 F 2s 没有查到**。
Ta 4f splitting is **1.92 eV** (three NIST records); the table value 1.91 is fine and hitting the 1.78 bound is an overlap effect. Ta 5p3/2 is at **37.3 eV** in Ta₂O₅ and 32.7 eV in the metal. Oxide O 2s lies at 21–23 eV. Fluoride F 2s lies at 28.4–31.8 eV; **no value found for fluoropolymer F 2s**.

| Line | BE (eV) | Material | Source (hν) | Citation | Label |
|---|---|---|---|---|---|
| Ta 4f splitting | 1.92 | Ta metal | non-monochromated, Au-calibrated | NIST SRD 20 record 34040 = Nyholm, Berndtsson, Mårtensson, J. Phys. C 13, L1091 (1980); also records 92480, 92481 | A |
| Ta 4f splitting | 1.92 | Ta metal ("Δmetal") | — | Thermo Fisher XPS reference page, tantalum | B |
| Ta 4f splitting | 1.9 | elemental table (23.5 − 21.6) | compilation | X-ray Data Booklet Table 1-1 | C |
| Ta 4f splitting | 1.9 | Ta¹⁺…Ta⁵⁺ in Ta₂O₅ films (used as constraint) | Al Kα, Thermo K-Alpha; O 1s set to 532 eV | Perez et al., Appl. Phys. A 124, 792 (2018), DOI 10.1007/s00339-018-2198-9 | A |
| Ta 4f7/2 | 21.8 / 23.0 / 26.2 | Ta metal / TaN / Ta₂O₅ | C 1s = 284.8 | Thermo Fisher XPS reference page, tantalum | B |
| Ta 4f7/2 / 4f5/2 | 21.6 / 23.5 | elemental table | compilation | X-ray Data Booklet Table 1-1 | A |
| Ta 5p3/2 | 37.30 | Ta₂O₅ | non-monochromated; gold reference | NIST SRD 20 record 31946 = Sarma & Rao, J. Electron Spectrosc. Relat. Phenom. 20, 25 (1980), DOI 10.1016/0368-2048(80)85003-1 | A |
| Ta 5p3/2 | 32.70 | Ta metal | non-monochromated, Au-calibrated | NIST SRD 20 record 31954 (Nyholm 1980); X-ray Data Booklet gives 32.7 | A |
| Ta 5p3/2 | 34.70 / 34.20 | TaS₂ / (SnS)₁.₁₆TaS₂ | — | NIST SRD 20 records 91167, 91173 | A |
| Ta 5p1/2 | 42.2 | Ta (elemental table); TaC₀.₉₅ 42.20 | — | X-ray Data Booklet Table 1-1; NIST record 94101 | A |
| "Loss feature" | about 33 / about 38 | Ta metal / Ta₂O₅ | — | Thermo Fisher XPS reference page, tantalum | B |
| O 2s | 22.00 | IrO₂ | non-monochromated; gold reference | NIST SRD 20 record 27394 = Riga et al., Phys. Scr. 16, 351 region (record prints "Phys. Scripta 16, 35"), 1977, DOI 10.1088/0031-8949/16/5-6/027 | A |
| O 2s | 22.50 | Co₃O₄ | Mg Kα; Au 4f7/2 = 84.00 | NIST SRD 20 record 48769 = Strydom & Strydom, Inorg. Chim. Acta 159, 191 (1989) | A |
| O 2s | 21.1 / 22.4 / 22.5 | RuO₂ / TiO₂ / Cr₂O₃ | — | NIST SRD 20 records 27392, 27414, 27417 | A |
| O 2s | 19.3–25.7 | 83 records, oxides and hydroxides overall | — | NIST SRD 20, O 2s query | A |
| O 2s | **unverified** | Ta₂O₅ | — | no NIST record; McLellan et al. fit an O 2s Gaussian under Ta 4f but the text retrieved gives no BE | unverified |
| O 2s amplitude | fixed at 5 % of O 1s | Ta oxide on Ta | synchrotron, 630–6000 eV | McLellan et al., arXiv:2301.04567v2, Supporting Information (journal version Adv. Sci., DOI 10.1002/advs.202300921) | A |
| F 2s | 28.40 | KF | — | NIST SRD 20 record 27308 | A |
| F 2s | 30.30, 30.80 | LiF | — | NIST SRD 20 records 27370, 111671 | A |
| F 2s | 29.9 / 30.3 / 29.9 / 29.25 / 31.80 | FeF₂ / FeF₃ / GdF₃ / SrF₂ / CaF₂ | — | NIST SRD 20 records 27311, 27310, 27307, 113114, 48658 | A |
| F 2s | "30 eV" | general | — | xpsfitting.com "Fluorine" page | B |
| F 2s | **unverified** | Nafion, PTFE | — | not found | unverified |

相对强度（自由原子截面，Scofield 1973，1.5 keV）/ Relative intensities (free-atom cross-sections, Scofield 1973 at 1.5 keV), label **C**:

| Ratio | Value | Formula (barn) |
|---|---|---|
| σ(Ta 5p3/2) / σ(Ta 4f total) | 0.089 | 10137 / (63826 + 50364) |
| σ(O 2s) / σ(O 1s) | 0.048 | 1871.5 / 38989 |
| σ(F 2s) / σ(F 1s) | 0.048 | 2803.7 / 58941 |
| σ(Ta 4f7/2) / σ(Ta 4f5/2) | 1.267 | 63826 / 50364 (statistical ratio is 1.333) |

备注 / Notes
- Ta₂O₅ 的 4f5/2 约在 26.2 + 1.92 = 28.1 eV。IrTaOx 中 34–35 eV 的峰不落在任何有出处的 Ta 4f 位置上；最接近的有出处的线是 Ta 5p3/2（氧化物 37.3，金属 32.7，硫化物 34.7）和氟化物 F 2s（上限 31.8）。
  Ta₂O₅ 4f5/2 is near 26.2 + 1.92 = 28.1 eV. A peak at 34–35 eV matches no sourced Ta 4f position; the nearest sourced lines are Ta 5p3/2 (37.3 oxide, 32.7 metal, 34.7 sulfide) and fluoride F 2s (up to 31.8).
- aged Ir-Ta 只剩 33.4 eV 一个峰：F 1s 在有机氟中比氟化物高约 4 eV（Thermo：688–689 对 684–685.5），如果 F 2s 同样上移，会落在 32–36 eV。这是推断，**未核实**。
  The single 33.4 eV peak in aged Ir-Ta: organic F 1s sits about 4 eV above fluorides (Thermo: 688–689 vs 684–685.5); if F 2s shifts likewise it would fall at 32–36 eV. This is an inference, **unverified**.
- F 2s 截面是 F 1s 的 4.8 %。Nafion 上 F 1s 是全谱最强峰，因此 F 2s 的强度可以和弱的 Ta 4f 相当。
  F 2s has 4.8 % of the F 1s cross-section. With F 1s the strongest survey peak on Nafion, F 2s can rival a weak Ta 4f.
- X-ray Data Booklet 给 O 的 L1 为 41.6 eV，与固体氧化物的 21–23 eV 不符，不要用作 O 2s 位置。
  The X-ray Data Booklet lists O L1 = 41.6 eV, inconsistent with 21–23 eV in solid oxides; do not use it for O 2s.

---

## F5 — IrO₂ 的 Ir 4f 线型；Co 3p 与 Ir 4f 的截面比 / IrO₂ Ir 4f line shape; Co 3p vs Ir 4f cross-sections

结论 / Bottom line: **实验室 Al Kα 数据应以 Freakley 2017 表 2 为准（F5a）**：无水 IrO₂ 用 LF(0.3, 1, 65, 100) 主峰加 +1.3 eV 的 GL(90) 卫星；水合/无定形 IrO₂ 用单个宽的非对称峰 LF(0.3, 1.5, 25, 150)。Pfeifer 2016 的参数是同步辐射的（F5b），Freakley 明确说它不能照搬到单色实验室光源。**Kahk 2014 正文没有给数值**，数值在其补充材料中，未取得。截面比 σ(Co 3p)/σ(Ir 4f) = **0.140**（每原子，Scofield 1973，1.5 keV）。
**For laboratory Al Kα data use Freakley 2017 Table 2 (F5a)**: anhydrous IrO₂ is an LF(0.3, 1, 65, 100) main line plus a GL(90) satellite at +1.3 eV; hydrated/amorphous IrO₂ is a single broad asymmetric LF(0.3, 1.5, 25, 150) peak. The Pfeifer 2016 parameters are synchrotron values (F5b), and Freakley states they do not transfer to a monochromatic laboratory source. **The Kahk 2014 main text gives no numbers**; they are in its Supplemental Material, which was not obtained. Cross-section ratio σ(Co 3p)/σ(Ir 4f) = **0.140** per atom (Scofield 1973 at 1.5 keV).

### F5a Freakley et al. 2017 — Al Kα 线型 / Al Kα line shapes

Source: Freakley, Ruiz-Esquius, Morgan, Surf. Interface Anal. 49, 794–799 (2017), DOI 10.1002/sia.6225, Table 2 (Ir levels) and Table 3 (O 1s), read from the publisher PDF. Label **A**.

**Opus 复核（2026-11-13）/ Opus review:** 表 2 与表 3 的每一行（位置、面积、劈裂、FWHM、线型字符串）都与用户提供的出版社 PDF 文本核对一致。
Every row of Tables 2 and 3 (positions, areas, splittings, FWHM, line-shape strings) checked against the publisher PDF supplied by the user: all match.

Conditions: Kratos Axis Ultra DLD (monochromatic Al Kα, 144 W) and Thermo K-Alpha+ (monochromatic Al Kα, 72 W); tables are for **20 eV pass energy**. Au 4f7/2 = 83.95 eV, Cu 2p3/2 = 932.63 eV; neutralised spectra referenced to C 1s = 284.8 eV. CasaXPS v2.3.17, Shirley background. Samples: Ir foil (Ar⁺-sputtered), IrO₂ anhydrous and hydrated (Alfa Aesar Premion), IrCl₃. FWHM stated ±0.2 eV. Line shapes: LF = CasaXPS "Functional Lorentzian", GL = Gaussian–Lorentzian product.

| Sample | Peak | BE (eV) | Area (%) | Doublet separation (eV) | FWHM (eV) | CasaXPS line shape |
|---|---|---|---|---|---|---|
| Ir metal | 4f7/2 | 60.8 | 57.2 | 3.0 | 0.84 | LF(0.6, 1, 150, 300) |
| Ir metal | 4f5/2 | 63.8 | 42.8 | | 0.86 | same |
| Ir metal | 5p3/2 | 48.1 | 66.7 | 15.0 | 2.84 | GL(30) |
| Ir metal | 5p1/2 | 63.1 | 33.3 | | 2.84 | GL(30) |
| IrO₂ anhydrous | 4f7/2 | 61.9 | 49.5 | 3.0 | 0.70 | LF(0.3, 1, 65, 100) |
| IrO₂ anhydrous | 4f5/2 | 64.9 | 37.1 | | 0.75 | same |
| IrO₂ anhydrous | 4f7/2 satellite | 63.2 | 7.7 | 3.0 | 3.64 | GL(90) |
| IrO₂ anhydrous | 4f5/2 satellite | 66.2 | 5.8 | | 3.64 | GL(90) |
| IrO₂ anhydrous | 5p3/2 | 49.7 | 66.8 | 15.0 | 3.90 | GL(30) |
| IrO₂ anhydrous | 5p1/2 | 64.7 | 33.2 | | 3.90 | GL(30) |
| IrO₂ hydrated | 4f7/2 | 62.5 | 57.2 | 3.0 | 1.60 | LF(0.3, 1.5, 25, 150) |
| IrO₂ hydrated | 4f5/2 | 65.5 | 42.8 | | 1.65 | same |
| IrO₂ hydrated | 5p3/2 | 50.2 | 66.8 | 15.0 | 3.88 | GL(30) |
| IrO₂ hydrated | 5p1/2 | 65.2 | 33.2 | | 3.88 | GL(30) |
| IrCl₃ hydrated | 4f7/2 / 4f5/2 | 62.6 / 65.6 | 56.1 / 42.0 | 3.0 | 0.94 / 1.05 | LF(1, 1, 55, 200) |
| IrCl₃ hydrated | 4f7/2 / 4f5/2 satellite | 71.6 / 74.6 | 1.1 / 0.8 | 3.0 | 1.24 / 1.24 | GL(30) |
| IrCl₃ anhydrous (Ir–Cl only) | 4f7/2 / 4f5/2 | 62.4 / 65.4 | 57.2 / 42.8 | 3.0 | 0.94 / 1.05 | LF(1, 1, 55, 200) |

O 1s (Table 3, 20 eV pass energy):

| Sample | Component | BE (eV) | FWHM (eV) | Line shape |
|---|---|---|---|---|
| IrO₂ anhydrous | oxide | 530.0 | 0.64 | LF(0.3, 1, 65, 100) |
| IrO₂ anhydrous | satellite | 531.3 | 2.16 | GL(90) |
| IrO₂ hydrated | oxide | 530.5 | 1.71 | LF(0.3, 1.5, 25, 150) |
| IrO₂ hydrated | hydroxide | 531.6 | 1.50 | GL(30) |
| IrO₂ hydrated | water | 532.9 | 1.60 | GL(30) |

由表算出 / Derived (label **C**): 无水 IrO₂ 卫星与主峰面积比 / satellite to main-line area ratio in anhydrous IrO₂ = 7.7 / 49.5 = 0.156; 卫星位移 / satellite offset = +1.3 eV（Ir 4f 与 O 1s 相同 / same for Ir 4f and O 1s）; 4f7/2 : 4f5/2 面积比 / area ratio = 57.2 : 42.8 = 1.336.

Statements in the paper (label **A**):
- 这些线型与 Pfeifer、Kahk 的不同；后者适用于 HAXPES，不能照搬到常规单色光源（见其图 S2）。/ These line shapes differ from those of Pfeifer and Kahk, which suit HAXPES and do not translate to a standard monochromatic source (their Figure S2).
- Ir 4f 的 Shirley 背景范围应较小（约 57–70 eV）；向高结合能侧延长会明显高估峰面积。/ The Shirley background for Ir 4f should span a small range (about 57–70 eV); extending it to higher BE significantly overestimates the area.
- Ir 5p1/2 在 4f 包络下面（距 5p3/2 约 15 eV），贡献估计小于 5 %，但应包含在拟合中；建议把采集范围扩到包含 5p3/2，并按 2 : 1 面积比、相同宽度、间距 15.0 eV 约束。/ Ir 5p1/2 lies under the 4f envelope (about 15 eV from 5p3/2), estimated below 5 %, but should be fitted; extend the acquisition range to include 5p3/2 and constrain 2 : 1 area ratio, equal FWHM, separation 15.0 eV.
- 水合（无定形）IrO₂ 含少量 Ir(III) 态，在常规单色光源下分不开；为简化，用一个宽的非对称峰包含 Ir(IV)、Ir(III) 及其卫星。/ Hydrated (amorphous) IrO₂ contains minority Ir(III) states that cannot be separated with a conventional monochromatic source; for simplicity one broad asymmetric peak covers Ir(IV), Ir(III) and their satellites.
- 无水 IrO₂ 的 O 1s 同样不对称，可用与 Ir 4f 相同的线型加卫星拟合，不需要额外的氧物种。/ O 1s of anhydrous IrO₂ is also asymmetric and is fitted with the same line shape plus a satellite, without extra oxygen species.
- Kratos 与 Thermo 两台仪器上线型可通用；同样通能下 Kratos 分辨率略好。/ The line shapes transfer between the Kratos and Thermo instruments; the Kratos has slightly better resolution at equal pass energy.
- LF 四个参数的定义在其补充材料中，**本次没有读到**。/ The definition of the four LF parameters is in their Supporting Information, **not read in this session**.

### F5b Pfeifer et al. 2016 — 同步辐射拟合模型 / synchrotron fit model

Source: Pfeifer, Jones, Velasco Vélez, Massué, Arrigo, Teschner, Girgsdies, Scherzer, Greiner, Allan, Hashagen, Weinberg, Piccinin, Hävecker, Knop-Gericke, Schlögl, "The electronic structure of iridium and its oxides", Surf. Interface Anal. 48, 261–273 (2016), DOI 10.1002/sia.5895; read from the MPG.PuRe author manuscript, Tables 1, 2 and 4. **Synchrotron**; spectra labelled by photoelectron kinetic energy (130, 450, 900 eV), not Al Kα. Shirley background, CasaXPS. Constraints in all fits: 4f7/2–4f5/2 separation 3 eV, area ratio 4:3 with ±5 % allowed. Label **A**.

Line-shape notation as defined in the paper: DS(α,n) is a Doniach–Šunjić profile with asymmetry α convoluted with a Gaussian of width index n (0–499); SGL(m) blends a Gaussian–Lorentzian sum form on the low-BE side (m = 0 Gaussian, 100 Lorentzian); GL(0) is a pure Gaussian.

| Material, KE | Component | Line shape | BE (eV) | FWHM (eV) | Area (%) |
|---|---|---|---|---|---|
| Ir(111), 130 eV | Ir⁰ 4f7/2 | DS(0.13,140)SGL(100) | 60.8 | 0.5 | 44.6 |
| Ir(111), 130 eV | Ir⁰ 4f5/2 | DS(0.13,140)SGL(100) | 63.8 | 0.5 | 29.0 |
| Ir(111), 130 eV | surface core level 4f7/2 | DS(0.13,140)SGL(100) | 60.4 | 0.6 | 16.0 |
| Ir(111), 130 eV | surface core level 4f5/2 | DS(0.13,140)SGL(100) | 63.4 | 0.5 | 10.4 |
| Ir(111), 900 eV | Ir⁰ 4f7/2 | DS(0.13,250)SGL(90) | 60.9 | 0.9 | 57.1 |
| Ir(111), 900 eV | Ir⁰ 4f5/2 | DS(0.13,250)SGL(90) | 63.9 | 0.9 | 42.9 |
| rutile IrO₂, 130 eV | Ir(IV) 4f7/2 | DS(0.2,100)SGL(65) | 61.7 | 0.6 | 44.6 |
| rutile IrO₂, 130 eV | Ir(IV) 4f5/2 | DS(0.2,100)SGL(65) | 64.7 | 0.7 | 34.8 |
| rutile IrO₂, 130 eV | Ir(IV) sat 1, 4f7/2 | GL(0) | 62.8 | 2.5 | 11.2 |
| rutile IrO₂, 130 eV | Ir(IV) sat 1, 4f5/2 | GL(0) | 65.8 | 2.6 | 8.4 |
| rutile IrO₂, 130 eV | Ir(IV) sat 2, 4f5/2 | GL(0) | 67.8 | 1.7 | 1.1 |
| rutile IrO₂, 900 eV | Ir(IV) 4f7/2 | DS(0.2,230)SGL(55) | 61.8 | 0.9 | 44.1 |
| rutile IrO₂, 900 eV | Ir(IV) 4f5/2 | DS(0.2,230)SGL(55) | 64.8 | 0.9 | 35.7 |
| rutile IrO₂, 900 eV | Ir(IV) sat 1, 4f7/2 | GL(0) | 62.9 | 2.6 | 10.4 |
| rutile IrO₂, 900 eV | Ir(IV) sat 1, 4f5/2 | GL(0) | 65.9 | 2.6 | 7.8 |
| rutile IrO₂, 900 eV | Ir(IV) sat 2, 4f5/2 | GL(0) | 67.9 | 2.5 | 2.1 |
| amorphous IrOₓ, 673 K in 25 Pa O₂, 130 eV | Ir(IV) 4f7/2 / 4f5/2 | DS(0.2,100)SGL(55) | 61.7 / 64.7 | 0.8 / 0.9 | 41.2 / 32.1 |
| same | Ir(IV) sat 1 (7/2, 5/2), sat 2 (5/2) | GL(0) | 62.8 / 65.8 / 67.8 | 2.5 / 2.6 / 2.0 | 10.3 / 7.9 / 1.3 |
| same | Ir(III) 4f7/2 / 4f5/2 | DS(0.2,100)SGL(55) | 62.3 / 65.3 | 0.9 / 1.0 | 3.5 / 2.6 |
| same | Ir(III) sat 1 (7/2, 5/2) | GL(0) | 63.3 / 66.3 | 2.3 / 2.4 | 0.6 / 0.4 |

由表算出 / Derived (label **C**): 卫星 1 与主峰的面积比 / satellite 1 to main-line area ratio = 11.2 / 44.6 = 0.251 (130 eV) and 10.4 / 44.1 = 0.236 (900 eV); 卫星 1 位移 / satellite 1 offset = +1.1 eV; 卫星 2 位移 / satellite 2 offset = +3.1 eV from 4f5/2.

Statements in the paper (label **A**):
- Ir 金属用单个 DS 函数即可，α = 0.13，与 Hüfner 等的 0.12 一致。/ Ir metal is fitted by a single DS function with α = 0.13, agreeing with 0.12 from Hüfner et al.
- IrO₂ 是金属性导体，但 4f 谱不能用单个 DS 函数拟合，需要在主峰上方约 1 eV 加一个高斯 shake-up 卫星，另在约 3 eV 处加第二个。/ IrO₂ is a metallic conductor, yet Ir 4f cannot be fitted with one DS function; a Gaussian shake-up satellite about 1 eV above the main line is required, and a second about 3 eV above.
- Ir 4f7/2 的第二卫星被 4f5/2 主峰完全盖住，拟合中未包含。/ The second satellite of 4f7/2 is buried under the 4f5/2 main line and is left out.
- 无定形 IrOₓ 中的 Ir(III) 在 62.3 eV，比 Ir(IV) **高** 0.6 eV。/ Ir(III) in amorphous IrOₓ sits at 62.3 eV, **above** Ir(IV) by 0.6 eV.
- Ir 5p1/2 约在 63 eV，被 Ir 4f 盖住；在他们的光子能量下截面不超过 4f 的 2 %，未拟合。/ Ir 5p1/2 lies near 63 eV under Ir 4f; at their photon energies it is at most 2 % of 4f and was omitted.
- 表 3（原样无定形 IrOₓ）的列在文本抽取中无法可靠对齐，未转录。/ Table 3 (as-received amorphous IrOₓ) could not be aligned reliably in text extraction and is not transcribed.

### F5c 其他来源 / Other sources

| Statement | Source (hν) | Citation | Label |
|---|---|---|---|
| Core lines of IrO₂ show strong satellites ascribed to final-state screening; a simple plasmon model is not valid for IrO₂ | HAXPES + DFT | Kahk et al., Phys. Rev. Lett. 112, 117601 (2014), DOI 10.1103/PhysRevLett.112.117601, abstract | A |
| Ir 4f will not fit with a single Voigt component or a Fano-type line shape; best fits use two Voigt components per core line (screened = low BE, unscreened = high BE, Kotani model), with constraints on the relative intensities of the two halves of each spin–orbit doublet and on the relative positions of the main peaks | HAXPES, 6.5 keV (SPring-8 BL12XU), plus other energies at GALAXIES (SOLEIL) | Kahk et al. 2014, p. 117601-4 and Fig. 1(b) | A |
| Constraining the screened–unscreened separation to one value for all core lines rapidly worsens the fits, so a simple plasmon model may not be appropriate for IrO₂ | same | Kahk et al. 2014, p. 117601-4 | A |
| Complex line shapes do not imply several oxidation states in the initial state | same | Kahk et al. 2014, p. 117601-4 | A |
| Component BEs, areas, FWHM and Gaussian/Lorentzian ratios of the screened / unscreened components | same | tabulated only in the Supplemental Material of Kahk et al. 2014 (their ref. [19]); not obtained | unverified |
| IrO₂(110) film on Ir(100): Ir 4f7/2 at 61.7 eV (bulk six-fold Ir), 61.3 eV (surface Ir_cus), 60.8 eV (bulk Ir metal), near 60.3 eV (surface atoms of clean Ir(100)); strong asymmetry from shake-up, intrinsic to IrO₂ | synchrotron, 720 eV and 250 eV | Martin et al., J. Phys. Chem. Lett. 11, 7184–7189 (2020), DOI 10.1021/acs.jpclett.0c01805 | A |
| Rutile IrO₂ maxima at 61.7 eV and 64.7 eV | synchrotron | Pfeifer et al. 2016, text | A |
| Ir 4f splitting 2.90, 2.90, 2.95, 3.01 (Ir metal); 2.90 (IrO₂) | — | NIST SRD 20 records 33989, 33991, 33986, 33987; 33993 | A |
| Mean Ir 4f7/2 compiled from NIST: Ir 60.8 ± 0.2, IrClₓ 62.2 ± 0.7, IrO₂ 61.9 ± 0.7 eV | compilation | Freakley et al. 2017, Table 1 | A |
| Ir 4f7/2 = 60.9 eV (metal); "Δ = 3.2 eV"; oxide peaks described as symmetric | — | Thermo Fisher XPS reference page, iridium | B |

Thermo 页面的两点与一手文献矛盾：劈裂 3.2 eV（NIST 2.90–3.01，Pfeifer 3 eV，Freakley 3.0 eV）；氧化物对称线型（Freakley、Pfeifer、Kahk、Martin 都指出 IrO₂ 固有不对称）。应以一手文献为准。
Two points on the Thermo page conflict with primary literature: splitting 3.2 eV (NIST 2.90–3.01, Pfeifer 3 eV, Freakley 3.0 eV) and symmetric oxide peaks (Freakley, Pfeifer, Kahk and Martin all report intrinsic asymmetry for IrO₂). Primary literature should prevail.

无水 IrO₂ 的 4f7/2 主峰位置两家差 0.2 eV：Freakley 61.9 eV（C 1s = 284.8 或导体直接测），Pfeifer 61.7 eV。卫星位移 +1.3 对 +1.1 eV，卫星/主峰面积比 0.156 对 0.25——卫星线型不同（GL(90) 对纯高斯）且主峰拖尾不同，两套参数不能混用。
The anhydrous IrO₂ 4f7/2 main line differs by 0.2 eV between the two: Freakley 61.9 eV, Pfeifer 61.7 eV. Satellite offset +1.3 vs +1.1 eV and satellite/main area ratio 0.156 vs 0.25 — the satellite shapes (GL(90) vs pure Gaussian) and main-line tails differ, so the two parameter sets must not be mixed.

### F5d 光电离截面 / Photoionisation cross-sections

Source: Scofield, "Theoretical Photoionization Cross Sections from 1 to 1500 keV", UCRL-51326, Lawrence Livermore Laboratory 1973, DOI 10.2172/4545040, as digitised by Kalha, Fernando, Regoutz (figshare DOI 10.6084/m9.figshare.12967079.v1), **row 1.5 keV**. Subshell cross-sections in barn per atom. Label **A** for barn values, **C** for ratios.

| Subshell | σ (barn) | σ / σ(C 1s) |
|---|---|---|
| C 1s | 13291 | 1.000 |
| Co 3p3/2 | 16963 | 1.276 |
| Co 3p1/2 | 8799.6 | 0.662 |
| Co 3p total | 25762.6 | 1.938 |
| Co 2p3/2 | 167890 | 12.63 |
| Co 2p1/2 | 86993 | 6.545 |
| Ir 4f7/2 | 103160 | 7.762 |
| Ir 4f5/2 | 81228 | 6.112 |
| Ir 4f total | 184388 | 13.87 |
| Ir 5p1/2 | 5688.1 | 0.428 |
| Ir 5p3/2 | 13002 | 0.978 |
| Ir 4d5/2 | 146250 | 11.00 |
| Ta 4f7/2 / 4f5/2 | 63826 / 50364 | 4.802 / 3.789 |
| Ta 5p3/2 | 10137 | 0.763 |
| O 1s / O 2s | 38989 / 1871.5 | 2.933 / 0.141 |
| F 1s / F 2s | 58941 / 2803.7 | 4.435 / 0.211 |
| K 2p3/2 / 2p1/2 | 34807 / 17886 | 2.619 / 1.346 |

| Ratio | Value | Formula |
|---|---|---|
| σ(Co 3p total) / σ(Ir 4f total) | **0.140** | 25762.6 / 184388 |
| σ(Co 3p total) / σ(Ir 4f7/2) | 0.250 | 25762.6 / 103160 |
| σ(Ir 5p1/2) / σ(Ir 4f total) | 0.031 | 5688.1 / 184388 |
| σ(Ir 4f7/2) / σ(Ir 4f5/2) | 1.270 | 103160 / 81228 (statistical ratio is 1.333) |

备注 / Notes
- **来源差异 / Source caveat.** 任务指定的是 Scofield 1976（J. Electron Spectrosc. Relat. Phenom. 8, 129–137，DOI 10.1016/0368-2048(76)80015-1，1487 eV，以 C 1s 为单位）。该表的数值本次没有取得。上表是同一作者 1973 年报告在 1.5 keV 的值，光子能量差 0.9 %。1973 表中 C 1s = 13291 barn，1976 文中 C 1s 归一值是否为 13600 barn **未核实**。比值对这 0.9 % 的差别预计不敏感，但请 Opus 决定是否需要取得 1976 原表。
  The task names Scofield 1976 (1487 eV, in units of C 1s); that table was not obtained. The numbers above are from the same author's 1973 report at 1.5 keV, 0.9 % higher in photon energy. Ratios should be insensitive to this, but Opus should decide whether the 1976 table is required.
- Co 3p 与 Ir 4f 的动能几乎相同（结合能都在 60 eV 附近），非弹性平均自由程与传输函数在比值中基本抵消。所以 Co 3p 面积 ≈ 0.140 × n(Co)/n(Ir) × Ir 4f 总面积；Co : Ir = 1 : 1 时 Co 3p 约为 Ir 4f 总面积的 14 %。角分布不对称参数的差别没有计入。
  Co 3p and Ir 4f have nearly the same kinetic energy, so the inelastic mean free path and transmission largely cancel. Co 3p area ≈ 0.140 × n(Co)/n(Ir) × total Ir 4f area; at Co : Ir = 1 : 1 Co 3p is about 14 % of total Ir 4f. Differences in angular asymmetry are not included.
- Co 3p 结合能：X-ray Data Booklet 表 1-1 给 M2 = 58.9、M3 = 59.9 eV（表中原样，3p1/2 低于 3p3/2，疑为表中排列问题）；NIST 给 Co 金属 3p 劈裂 1.10 eV（记录 33701）。**氧化态 Co 的 3p 位置（C0 写的 60–61 eV）没有查到出处。**
  Co 3p BE: the X-ray Data Booklet lists M2 = 58.9 and M3 = 59.9 eV as printed (3p1/2 below 3p3/2, probably a table artefact); NIST gives a Co metal 3p splitting of 1.10 eV (record 33701). **No source found for Co 3p in oxides (60–61 eV in C0).**
- Al Kα 下 Ir 5p1/2 是 Ir 4f 的 3.1 %，高于 Pfeifer 在软 X 射线下估计的 2 %，与 Freakley 的"小于 5 %"一致。Freakley 给出 5p1/2 位置：金属 63.1、无水 IrO₂ 64.7、水合 IrO₂ 65.2 eV，宽 2.8–3.9 eV。
  With Al Kα, Ir 5p1/2 is 3.1 % of Ir 4f, above Pfeifer's 2 % estimate for soft X-rays and consistent with Freakley's "less than 5 %". Freakley gives the 5p1/2 position: 63.1 (metal), 64.7 (anhydrous IrO₂), 65.2 eV (hydrated IrO₂), FWHM 2.8–3.9 eV.

---

## F6 — Nafion 上催化剂的差分荷电：可用来判别的证据 / Differential charging of catalyst on Nafion: what would distinguish it

没有做数据分析，下面只列判据。样品结构用户已确认，见表后。
No data analysis was done; only the criteria are listed. The sample structure has been confirmed by the user, see below the table.

| # | 判据 / Criterion | 差分荷电时 / If differential charging | 化学位移时 / If chemical shift | 依据 / Basis |
|---|---|---|---|---|
| 1 | 同一相的所有芯能级是否平移同一数值（Ir 4f、Ir 4d5/2、晶格 O 1s）/ Do all core levels of one phase shift by the same amount? | 相同 / identical | 各能级位移不同 / differs by level | 荷电是刚性平移 / charging is a rigid shift (Baer et al. 2020; ASTM E1523) |
| 2 | 催化剂线与膜线需要的校正量是否不同（膜：CF₂ 292.2、F 1s 689.7、S 2p 170.1 eV）/ Do catalyst lines and membrane lines need different corrections? | 不同 / different | 相同 / same | F1c 的 Nafion 参考值 / Nafion reference values in F1c (Friedman 2018) |
| 3 | 俄歇参数或同元素两条线的间距（例：Ir 4d5/2 与 Ir 4f7/2 之差，数值见表后）/ Auger parameter, or separation of two lines of one element (Ir 4d5/2 − Ir 4f7/2, values below the table) | 不变 / unchanged | 可变 / may change | 间距与荷电无关 / separations are charge-independent |
| 4 | 峰是否展宽、出现形状相同的重复峰或肩峰 / Broadening, duplicated peaks or shoulders of identical shape | 有 / present | 无 / absent | Baer et al. 2020; ASTM E1523 |
| 5 | 改变中和枪设置或 X 射线功率后峰位是否移动 / Do positions move with flood-gun setting or X-ray power? | 移动 / move | 不动 / fixed | Baer et al. 2020 |
| 6 | 价带费米边（IrO₂ 是金属性导体，校正后应在 0 eV）/ Valence-band Fermi edge (IrO₂ is metallic; should be at 0 eV after correction) | 偏离 0 且与芯能级偏移一致 / offset from 0 by the same amount as core levels | 在 0 / at 0 | Pfeifer 2016; Greczynski & Hultman 2020 |
| 7 | 接地方式：样品浮地与接地各测一次 / Mounting: measure floating and grounded | 结果不同 / results differ | 相同 / same | Baer et al. 2020 |
| 8 | 辐照时间序列：F 1s、C 1s 是否随时间变化 / Time series: do F 1s and C 1s change with exposure? | — | X 射线损伤的迹象 / sign of X-ray damage | Thermo fluorine page: fluoropolymers are X-ray sensitive |

与文献值对照 / Against sourced values: 本文件中有出处的 Ir 4f7/2 为：金属 60.8–60.9，无水 IrO₂ 61.7–61.9，无定形 IrOₓ 的 Ir(III) 62.3，水合 IrO₂ 62.5，IrCl₃ 62.4–62.6 eV（Freakley 2017；Pfeifer 2016；Martin 2020）。aged Ir-Ta 的 63.4–65.1 eV 比其中最高的还高 0.8–2.5 eV。**氟化物等其他 Ir 化合物的 4f7/2 本次没有查**，所以不能单凭这一点排除化学原因。
Sourced Ir 4f7/2 values in this file: metal 60.8–60.9, anhydrous IrO₂ 61.7–61.9, Ir(III) in amorphous IrOₓ 62.3, hydrated IrO₂ 62.5, IrCl₃ 62.4–62.6 eV. The 63.4–65.1 eV of aged Ir-Ta is 0.8–2.5 eV above the highest of these. **Ir 4f7/2 of other compounds such as fluorides was not looked up**, so a chemical origin cannot be excluded on this alone.

判据 3 可直接用 Freakley 的数值：Ir 4d5/2 − Ir 4f7/2 = 235.4 eV（金属），236.2 eV（无水 IrO₂），236.1 eV（水合 IrO₂）。这个差与荷电无关；若 aged 样品的差值落在 236.1–236.2 eV，说明是 IrO₂ 整体平移（荷电），不是新的化学态。标签 C。
Criterion 3 can use Freakley's numbers directly: Ir 4d5/2 − Ir 4f7/2 = 235.4 eV (metal), 236.2 eV (anhydrous IrO₂), 236.1 eV (hydrated IrO₂). The difference is charge-independent; if the aged sample gives 236.1–236.2 eV, the lines are IrO₂ shifted rigidly (charging), not a new chemical state. Label C.

**用户确认的样品结构（2026-11-12）/ Sample structure confirmed by the user**
- 催化剂与 Nafion 配成 ink，喷涂在 Nafion 膜上。/ Catalyst and Nafion are mixed into an ink and sprayed onto the Nafion membrane.
- 催化层约 10 μm 厚，连续。/ The catalyst layer is about 10 μm thick and continuous.
- 样品台接地方式、中和枪设置：未知。是否采了 Ir 4d 或价带谱：未知。/ Grounding and flood-gun settings: unknown. Whether Ir 4d or valence-band spectra were taken: unknown.

由此得到 / What follows
- 10 μm 远大于 XPS 的取样深度（几个纳米），所以信号全部来自催化层本身（催化剂颗粒加离聚物），下面的膜看不到。谱里的 F 1s、CF₂ 来自催化层内的离聚物，适用 F1d 的数值（CFₓ 约 290.5 eV，F 1s 约 687.7 eV），不适用膜的 292.2 / 689.7 eV。
  10 μm is far more than the XPS sampling depth (a few nanometres), so the signal comes entirely from the catalyst layer itself (catalyst particles plus ionomer); the membrane underneath is not seen. F 1s and CF₂ in the spectra come from ionomer inside the layer, for which the F1d values apply (CFₓ about 290.5 eV, F 1s about 687.7 eV), not the membrane values 292.2 / 689.7 eV.
- 催化层坐在绝缘的膜上，对地没有导电通路，整层可以浮动；层内导电的催化剂网络与绝缘的离聚物还可以再相差约 1.7 eV（Dzara 2024）。老化后若催化层开裂或催化剂流失，导电网络断开，就会出现判据 4 的展宽和重复峰。这是推断，要靠判据 1–3 在数据上检验。
  The layer sits on an insulating membrane with no conductive path to ground, so the whole layer can float; inside it the conductive catalyst network and the insulating ionomer can differ by a further 1.7 eV or so (Dzara 2024). If ageing cracks the layer or removes catalyst, the network breaks up and the broadening and duplicated peaks of criterion 4 would appear. This is an inference to be tested on the data with criteria 1–3.
- **不需要新测量就能做的检验 / Tests that need no new measurement:** C 1s 窗口已经包含 Ir 4d5/2。在现有的 aged Ir-Ta 谱上读出 Ir 4d5/2 − Ir 4f7/2：若为 236.1–236.2 eV（IrO₂，Freakley 2017），说明 Ir 4f 的 63.4–65.1 eV 是整体平移。再看 Ir 4f 相对于同一谱中 CF₂ 和 F 1s 的间距是否与 pristine 样品相同。
  The C 1s window already contains Ir 4d5/2. Read Ir 4d5/2 − Ir 4f7/2 from the existing aged Ir-Ta spectra: 236.1–236.2 eV (IrO₂, Freakley 2017) means the 63.4–65.1 eV of Ir 4f is a rigid shift. Also compare the separation of Ir 4f from CF₂ and F 1s in the same sample with that of the pristine sample.
- 采谱设置可从 PHI .spe 文件头读出（中和枪、通能等），不必靠回忆；这一步留给 Opus。/ Acquisition settings (neutraliser, pass energy) can be read from the PHI .spe headers instead of from memory; left to Opus.

---

## G — 通用化：全元素可用的数据源 / Generalisation: all-element data sources

用户要求（2026-11-12）：不只解决这几个元素，所有元素都要能分析。下列来源覆盖全周期表，可让重叠线警告、劈裂约束、面积比按数据驱动，不必逐元素硬编码。
User requirement (2026-11-12): not only these elements; every element must be analysable. The sources below cover the whole periodic table, so overlap warnings, splitting constraints and area ratios can be data-driven instead of hard-coded per element.

| 需求 / Need | 来源 / Source | 覆盖 / Coverage | 注意 / Caveat |
|---|---|---|---|
| 任一元素所有芯能级的位置（找重叠线）/ All core-level positions of any element (overlap detection) | X-ray Data Booklet Table 1-1 (xdb.lbl.gov) | Z = 1–92, K 到 P 层 / K to P shells | 元素态数值；O 2s 等浅能级不适用于化合物 / elemental values; shallow levels such as O 2s do not apply to compounds |
| 化学态结合能、双峰劈裂、俄歇动能 / Chemical-state BEs, doublet separations, Auger KEs | NIST SRD 20 v5.0, DOI 10.18434/T4T88K; 查询地址 / query pattern `srdata.nist.gov/xps/QueryByElmType/{El}/{PE|DS|A}` | 22 000 余条 / over 22 000 lines | 多为非单色源；同一化合物分散可达 1 eV；使用条款需确认 / mostly non-monochromated; scatter up to 1 eV; terms of use to be checked |
| 俄歇线在结合能标尺上的位置 / Auger lines on the BE scale | `BE = hν − KE`，KE 取自 NIST / KE from NIST | 任意光源 / any source | 位置随光源变；Al Kα 与 Mg Kα 相差 233.0 eV / position depends on the source |
| 子壳层截面（面积比、重叠线强度估计）/ Subshell cross-sections (area ratios, overlap intensity) | Scofield 1973 数字化表 / digitised, figshare DOI 10.6084/m9.figshare.12967079.v1 | Z = 1–100 全部子壳层 / all subshells | 1.5 keV 行不是 1486.6 eV；随软件分发前需确认许可 / the 1.5 keV row is not 1486.6 eV; licence must be checked before bundling |
| 3d 过渡金属 2p 多重态 / 3d transition-metal 2p multiplets | Biesinger et al. 2011（Cr、Mn、Fe、Co、Ni；本文件只转录了 Co 的表 5）/ only Table 5 for Co is transcribed here | 5 种元素 / 5 elements | 仅 2p3/2；Kratos Axis Ultra 的宽度 / 2p3/2 only; widths are for a Kratos Axis Ultra |
| 导体的非对称线型 / Asymmetric shapes for conductors | 金属 DS 或 LA；导电氧化物加卫星（Pfeifer 2016 的 IrO₂ 为例）/ DS or LA for metals; conducting oxides need satellites | 规则，不是表 / a rule, not a table | 每种导电氧化物的卫星参数需单独出处 / each conducting oxide needs its own sourced satellite parameters |

由本文件数据得到的两条通用规则 / Two general rules supported by the data in this file
- 双峰面积比用截面比而非统计权重更接近实际：Ir 4f 1.270（统计 1.333），Ta 4f 1.267（1.333），Co 2p 1.930（2.000），K 2p 1.946（2.000）。/ Doublet area ratios from cross-sections differ from statistical weights: Ir 4f 1.270 (1.333), Ta 4f 1.267 (1.333), Co 2p 1.930 (2.000), K 2p 1.946 (2.000).
- 浅芯能级的强度可由同元素的强线估计：O 2s ≈ 4.8 % × O 1s，F 2s ≈ 4.8 % × F 1s（未计动能差）。/ Shallow-level intensity can be estimated from the strong line of the same element: O 2s ≈ 4.8 % × O 1s, F 2s ≈ 4.8 % × F 1s (kinetic-energy difference neglected).

---

## H — CasaXPS 线型的定义 / Definition of the CasaXPS line shapes

为什么需要 / Why it matters: Biesinger 2011 的 Co 金属用 `LA(1.2,5,5)`，Freakley 2017 的 Ir/IrO₂ 用 `LF(α, β, w, m)`。要在 PeakForge 里重现这些预设，必须知道这两个函数的数学形式。
Biesinger 2011 uses `LA(1.2,5,5)` for Co metal and Freakley 2017 uses `LF(α, β, w, m)` for Ir/IrO₂. Reproducing these presets in PeakForge needs the mathematical form of both.

结论 / Bottom line: **LA 的定义已取得；LF 的定义在 casaxps.com/manual.html 列出的文档里没有找到。**
**The LA definition was obtained; the LF definition is not in the documents listed at casaxps.com/manual.html.**

### H1 LA — 已取得 / obtained

Source: Supplementary Information to Fairley et al., J. Vac. Sci. Technol. A 41(1) (2023), DOI 10.1116/6.0002196, distributed as `casaxps.com/pdfs/XPS-of-Nylon-rev5.pdf`, p. 8, Equations (2)–(6); read from the rendered page. Label **A**.

| Eq. | Definition |
|---|---|
| (2) Lorentzian | `l(x) = 1 / (1 + 4x²)` |
| (3) Gaussian | `g(x) = exp(−4 ln2 · x²)` |
| (4) Generalised Lorentzian | `l_g(x: α, β) = [l(x)]^α` for `x ≤ 0`; `[l(x)]^β` for `x > 0` |
| (5) Line shape | `LA(x: α, β, n) = N ∫ l_g(τ: α, β) · g(x − τ : f_G(n)) dτ` over `−∞ … ∞` |
| (6) One-parameter form | `LA(x, m) = LA(x: 1, 1, 1401 − (m/100)·1401)` |

Statements in the CasaXPS documents (label **A**):
- α = β = 1 给出 Voigt 函数；α ≠ β 引入不对称。/ α = β = 1 gives a Voigt function; α ≠ β introduces asymmetry. (Nylon SI p. 7; Cookbook 2026 p. 19)
- `LA(1,1,0)` 是纯洛伦兹；n 越大，卷积里的高斯越宽。/ `LA(1,1,0)` is a pure Lorentzian; larger n widens the Gaussian in the convolution. (Cookbook 2026, Fig. 15)
- LA 可写成一、二、三个参数：`LA(50)`、`LA(1,701)`、`LA(1,1,701)`；`LA(m)` 用来对应历史上的 `GL(m)`。1401 是高斯宽度上限的任意取值，所以 `LA(0)` 不是纯高斯。/ LA takes one, two or three parameters; `LA(m)` mirrors the historical `GL(m)`. 1401 is an arbitrary upper limit for the Gaussian width, so `LA(0)` is not a pure Gaussian.
- `GL(m)`、`SGL(m)` 是伪 Voigt（乘积式与求和式），m = 0 纯高斯，m = 100 纯洛伦兹。/ `GL(m)` and `SGL(m)` are pseudo-Voigt forms; m = 0 is pure Gaussian, m = 100 pure Lorentzian.
- Biesinger 2011 的说明与此一致：`LA(α, β, m)` 中 α、β 决定洛伦兹两侧拖尾的展开，m 是卷积用的高斯宽度；α、β 大于 1 时可避免旧式非对称线型把远离峰位的面积算进去。/ Biesinger 2011 agrees: in `LA(α, β, m)`, α and β set the spread of the tail on either side and m is the width of the convolving Gaussian; values above unity avoid counting area far above the peak.

### H2 仍然缺的 / Still missing

| Item | Status |
|---|---|
| `LF(α, β, w, m)` 的定义，尤其第三个参数 w / definition of `LF(α, β, w, m)`, in particular the third parameter w | **unverified.** 在下列文档中检索 "LF(" 均为 0 次：Cookbook 2026（189 页）、Roscoff 2019 汇编、TestPeakModel、CasaXPS 2.3.25 Review、Quantification Parameters、Nylon SI。这些新文档改用 `TLA` / `ST` 修饰。Freakley 称 LF 为 "Functional Lorentzian"，并说详情在其补充材料中（用户确认下载不到）。/ "LF(" occurs zero times in all six documents; the current manuals use `TLA` / `ST` modifiers instead. Freakley calls LF "Functional Lorentzian" and refers to a Supporting Information the user could not obtain. |
| `f_G(n)`：整数 n 与高斯半高宽（单位为洛伦兹宽度或数据步长）的换算 / mapping from the integer n to the Gaussian FWHM | **unverified.** 式 (5) 只写成 `f_G(n)`，没有给出函数。/ Equation (5) only writes `f_G(n)`. |
| x 的符号约定：`x ≤ 0` 对应高结合能侧还是低结合能侧 / sign convention of x (which side is high BE) | **unverified.** 文档没有明说。/ Not stated explicitly. |
| `DS(α, n)` 的公式 / formula of `DS(α, n)` | Cookbook 2026 给了定义（Doniach–Šunjić 轮廓与宽度参数为 n 的高斯卷积），但公式在文本抽取中损坏，本次没有转录。/ Defined in Cookbook 2026 (Doniach–Šunjić profile convolved with a Gaussian of width parameter n), but the formula was garbled in text extraction and is not transcribed. |

对实现的含义（供 Opus 判断）/ Implication for implementation (for Opus to judge)
- `LA(α, β, m)` 的函数形式有出处，可以实现；但 n 到高斯宽度的换算没有出处，所以 `LA(1.2,5,5)` 里的 "5" 不能直接换成 eV。可行的做法是：采用式 (4)–(5) 的函数形式，把高斯宽度作为以 eV 为单位的拟合参数，预设里只固定 α、β。
  The functional form of `LA(α, β, m)` is sourced and can be implemented, but the mapping from n to a Gaussian width is not, so the "5" in `LA(1.2,5,5)` cannot be converted to eV. A workable route: adopt the form of Equations (4)–(5), keep the Gaussian width as a fit parameter in eV, and fix only α and β in the preset.
- Freakley 的 `LF` 字符串在定义取得之前不能逐字实现。在此之前，IrO₂ 预设可以用的有出处的量是：峰位、FWHM、劈裂 3.0 eV、面积比、卫星位置与相对面积、5p1/2 的位置与约束（F5a）；线型本身只能说明"非对称、高结合能侧拖尾"，具体参数要对标准样品重新标定。
  Freakley's `LF` strings cannot be implemented verbatim until the definition is found. Until then the sourced quantities usable for an IrO₂ preset are positions, FWHM, the 3.0 eV splitting, area ratios, satellite position and relative area, and the 5p1/2 position and constraints (F5a); the line shape itself can only be described as asymmetric with a high-BE tail, and its parameters would have to be calibrated on a reference sample.

---

## I — Cr、Mn、Fe、Ni 2p3/2（Biesinger 2011 表 1、3、4、6）/ Cr, Mn, Fe, Ni 2p3/2 (Biesinger 2011 Tables 1, 3, 4, 6)

转录与复核：Opus，2026-11-13。数值本身只存一处：`src/peakforge/data/multiplets.json`（每个化学态 [BE, 面积 %, FWHM]）。
Transcribed and checked by Opus, 2026-11-13. The numbers live in one place only: `src/peakforge/data/multiplets.json`.

方法 / Method
1. 期刊 PDF（surfacesciencewestern.com 上的出版社版本）按页渲染成图像，逐格目读（表格在 PDF 文本层中行列错乱）。/ Journal PDF pages rendered to images and read cell by cell (the text layer scrambles the rotated tables).
2. 每个数值都在该页 PDF 文本层中出现（自动核对）；唯一例外是下面的更正值 712.4。/ Every value occurs in that page's PDF text layer (automatic check); the only exception is the corrected value 712.4 below.
3. 每行的 Δ（相邻峰间距）与峰位之差逐一核对；每个化学态面积和为 100 %（±0.3）。/ Every Δ checked against the position differences; areas sum to 100 % (±0.3) per species.

采用的表与通能 / Tables and pass energy used
| 元素 | 表 | FWHM 通能 | 说明 / Notes |
|---|---|---|---|
| Cr | 1 | 20 eV（NiCr₂O₄ 只印了 10 eV） | Cr₂O₃ 面积按原文合计 103 %；Cr(III) 氢氧化物 577.3 为陈化样品（新鲜 577.1）；Cr(0) 为 LA(1.3,4,5) |
| Mn | 3（本文 Kratos 实测；表 2 为 SSX-100 文献汇编，不用） | 20 eV | MnO 峰 6 为 shake-up，FWHM 3.5；**软锰矿（pyrolusite）未收录：原文面积合计 80.1 %**（疑峰 1 应为 41.0，不猜）；Mn(0) 为 LA(1.1,3.2,3) |
| Fe | 4 | 10 eV（FeCr₂O₄ 20 eV） | Fe₃O₄ = Fe²⁺ 与 Fe³⁺ 两组合计 100 %；平均行（Ave.）不收录；Fe(0) 为 LA(1.2,4.8,3) |
| Ni | 6 | 20 eV（γ/β-NiOOH、NiCr₂O₄ 用 10 eV） | Ni(0) 取 “New Line Shape” 行，LA(1.1,2.2,10)；β-NiOOH = Ni³⁺ 与 Ni²⁺ 两组（2:1）合计 100 %；NiCr₂O₄ 峰 3 的 20 eV 宽度 7.01 与 10 eV 的 3.91 不符，故整行用 10 eV |

原文印刷不一致，按间距更正（原文脚注 a：间距比绝对结合能准确）/ Printed inconsistencies, resolved with the splittings (footnote a: splittings are more accurate than absolute BEs)
| 化学态 | 原文 | 采用 | 依据 |
|---|---|---|---|
| α-Fe₂O₃ 峰 4 | 713.3 | **712.3** | 711.4 + 0.9 = 712.3；713.3 − 1.0（峰 5）= 712.3 |
| α-FeOOH 峰 4 | 711.2 | **713.3** | 712.1 + 1.21 = 713.3；714.4 − 1.2 = 713.2 |
| FeCr₂O₄ 峰 4 | 713.0 | **712.4** | 711.2 + 1.2 = 712.4；713.8 − 1.4 = 712.4 |
| γ-Fe₂O₃ Δ(3−2) | 13.0 | 1.0 | 711.8 − 710.8；峰位本身不变 |

金属的非对称主峰（LA）在 PeakForge 中用 GL(30) 近似：CasaXPS LA 第三参数与高斯宽度的换算未公开（见 H 节）。/ Metallic asymmetric main lines (LA) are approximated by GL(30): the CasaXPS LA width mapping is unpublished (section H).

---

## 参考文献 / References

访问方式 / Access: **[PDF]** 本次读到原文文本 / paper text read in this session; **[DB]** 数据库记录 / database record; **[web]** 网页 / web page; **[abs]** 仅摘要 / abstract only; **[not read]** 未读到 / not read.

1. M. C. Biesinger, B. P. Payne, A. P. Grosvenor, L. W. M. Lau, A. R. Gerson, R. St. C. Smart, "Resolving surface chemical states in XPS analysis of first row transition metals, oxides and hydroxides: Cr, Mn, Fe, Co and Ni", Appl. Surf. Sci. 257, 2717–2730 (2011). DOI 10.1016/j.apsusc.2010.10.051 (DOI from memory, not re-checked). [PDF, surfacesciencewestern.com]
2. V. Pfeifer, T. E. Jones, J. J. Velasco Vélez, C. Massué, R. Arrigo, D. Teschner, F. Girgsdies, M. Scherzer, M. T. Greiner, J. Allan, M. Hashagen, G. Weinberg, S. Piccinin, M. Hävecker, A. Knop-Gericke, R. Schlögl, "The electronic structure of iridium and its oxides", Surf. Interface Anal. 48, 261–273 (2016). DOI 10.1002/sia.5895. [PDF, MPG.PuRe author manuscript; volume and pages as given in the task, not printed in the manuscript]
3. J. M. Kahk, C. G. Poll, F. E. Oropeza, J. M. Ablett, D. Céolin, J.-P. Rueff, S. Agrestini, Y. Utsumi, K. D. Tsuei, Y. F. Liao, F. Borgatti, G. Panaccione, A. Regoutz, R. G. Egdell, B. J. Morgan, D. O. Scanlon, D. J. Payne, "Understanding the Electronic Structure of IrO₂ Using Hard-X-ray Photoelectron Spectroscopy and Density-Functional Theory", Phys. Rev. Lett. 112, 117601 (2014). DOI 10.1103/PhysRevLett.112.117601. [PDF, main text; Supplemental Material not read]
4. S. J. Freakley, J. Ruiz-Esquius, D. J. Morgan, "The X-ray photoelectron spectra of Ir, IrO₂ and IrCl₃ revisited", Surf. Interface Anal. 49, 794–799 (2017). DOI 10.1002/sia.6225. [PDF, publisher version; Supporting Information not read]
5. R. Martin, M. Kim, C. J. Lee, V. Mehar, S. Albertin, U. Hejral, L. R. Merte, E. Lundgren, A. Asthagiri, J. F. Weaver, "High-Resolution X-ray Photoelectron Spectroscopy of an IrO₂(110) Film on Ir(100)", J. Phys. Chem. Lett. 11, 7184–7189 (2020). DOI 10.1021/acs.jpclett.0c01805. [PDF, OSTI]
6. A. K. Friedman, W. Shi, Y. Losovyj, A. R. Siedle, L. A. Baker, "Mapping Microscale Chemical Heterogeneity in Nafion Membranes with X-ray Photoelectron Spectroscopy", J. Electrochem. Soc. 165, H733 (2018). DOI 10.1149/2.0771811jes. [web, first half of the article verbatim]
7. G. Beamson, D. Briggs, High Resolution XPS of Organic Polymers: The Scienta ESCA300 Database, Wiley, Chichester, 1992. [not read; quoted via ref. 13 and NIST]
8. J. H. Scofield, "Theoretical Photoionization Cross Sections from 1 to 1500 keV", UCRL-51326, Lawrence Livermore Laboratory, 1973. DOI 10.2172/4545040. Digitised by C. Kalha, N. K. Fernando, A. Regoutz, figshare DOI 10.6084/m9.figshare.12967079.v1. [spreadsheet read]
9. J. H. Scofield, "Hartree–Slater subshell photoionization cross-sections at 1254 and 1487 eV", J. Electron Spectrosc. Relat. Phenom. 8, 129–137 (1976). DOI 10.1016/0368-2048(76)80015-1. [not read]
10. NIST X-ray Photoelectron Spectroscopy Database, NIST Standard Reference Database 20, Version 5.0 (A. V. Naumkin, A. Kraut-Vass, S. W. Gaarenstroom, C. J. Powell). DOI 10.18434/T4T88K. Record ids are given in the tables. [DB]
11. X-ray Data Booklet, Lawrence Berkeley National Laboratory, Table 1-1 "Electron binding energies", xdb.lbl.gov. [web]
12. Thermo Fisher Scientific, XPS reference table of elements (pages for cobalt, tantalum, iridium, fluorine, potassium, carbon, oxygen), thermofisher.com. [web]
13. M. C. Biesinger, "X-ray Photoelectron Spectroscopy (XPS) Reference Pages", xpsfitting.com (pages "Fluorine", "Cobalt"). [web]
14. I. Perez, V. Sosa, F. Gamboa, J. T. Elizalde Galindo, J. L. Enríquez-Carrejo, R. Farías, P. G. Mani González, "Influence of post-deposition annealing on the chemical states of crystalline tantalum pentoxide films", Appl. Phys. A 124, 792 (2018). DOI 10.1007/s00339-018-2198-9. [arXiv:1804.09538v2]
15. R. A. McLellan, A. Dutta, et al., N. P. de Leon, "Chemical profiles of the oxides on tantalum in state of the art superconducting circuits", arXiv:2301.04567v2 (2023); journal version Adv. Sci., DOI 10.1002/advs.202300921 (volume and page not checked). [PDF]
16. R. Nyholm, A. Berndtsson, N. Mårtensson, J. Phys. C: Solid State Phys. 13, L1091 (1980). DOI 10.1088/0022-3719/13/36/009. [via NIST records 30574, 34040, 31954]
17. D. D. Sarma, C. N. R. Rao, J. Electron Spectrosc. Relat. Phenom. 20, 25 (1980). DOI 10.1016/0368-2048(80)85003-1. [via NIST record 31946]
18. L. G. Petersson, S. E. Karlsson, Phys. Scr. 16, 425 (1977). DOI 10.1088/0031-8949/16/5-6/041. [via NIST record 33307]
19. C. D. Wagner, W. M. Riggs, L. E. Davis, J. F. Moulder, G. E. Muilenberg, Handbook of X-ray Photoelectron Spectroscopy, Perkin-Elmer, Eden Prairie, 1979. [via NIST records 33320, 33252, 33413]
20. T. J. Chuang, C. R. Brundle, D. W. Rice, Surf. Sci. 59, 413 (1976). DOI 10.1016/0039-6028(76)90026-1. [via NIST record 33392]
21. D. C. Frost, C. A. McDowell, I. S. Woolsey, Chem. Phys. Lett. 17, 320 (1972). DOI 10.1016/0009-2614(72)87086-6. [via NIST record 33287]
22. C. V. Schenck, J. G. Dillard, J. W. Murray, J. Colloid Interface Sci. 95, 398 (1983). DOI 10.1016/0021-9797(83)90199-6. [via NIST record 33303]
23. A. Lebugle, U. Axelsson, R. Nyholm, N. Mårtensson, Phys. Scr. 23, 825 (1981). DOI 10.1088/0031-8949/23/5A/013. [via NIST record 33246]
24. J. Riga, C. Tenret-Noël, J. J. Pireaux, R. Caudano, J. J. Verbist, Y. Gobillon, Phys. Scr. 16 (1977). DOI 10.1088/0031-8949/16/5-6/027 (page number as printed in the NIST record: "16, 35"; not re-checked). [via NIST record 27394]
25. C. A. Strydom, H. J. Strydom, Inorg. Chim. Acta 159, 191 (1989). DOI 10.1016/S0020-1693(00)80566-6. [via NIST record 48769]
26. A. P. Grosvenor, S. D. Wik, R. G. Cavell, A. Mar, Inorg. Chem. 44, 8988 (2005). [cited by ref. 1]
27. J. Yang, H. Liu, W. N. Martens, R. L. Frost, J. Phys. Chem. C 114, 111 (2010). [cited by ref. 1]
31. M. J. Dzara, K. Artyushkova, J. Foster, H. Eskandari, Y. Chen, S. A. Mauger, P. Atanassov, K. Karan, S. Pylypenko, "X-ray Photoelectron Spectroscopy Analysis of Nafion-Containing Samples: Pitfalls, Protocols, and Perceptions of Physicochemical Properties", J. Phys. Chem. C 128, 8467–8482 (2024). DOI 10.1021/acs.jpcc.4c00872. [PDF, publisher version, CC-BY 4.0; Supporting Information not read]
32. N. Fairley et al., "Practical guide to understanding goodness-of-fit metrics used in chemical state modeling of x-ray photoelectron spectroscopy data by synthetic lineshapes using nylon as an example", J. Vac. Sci. Technol. A 41(1) (2023). DOI 10.1116/6.0002196. Supplementary Information, casaxps.com/pdfs/XPS-of-Nylon-rev5.pdf. [PDF]
33. Casa Software Ltd, The CasaXPS Cookbook 2026 (casaxps.com/pdfs/CasaXPSCookbook2026.pdf); Roscoff 2019 manual compilation; "Constructing Line Shapes: Test Peak Model"; CasaXPS 2.3.25 Review; all linked from casaxps.com/manual.html. [PDF, searched for LA / LF definitions]
28. D. R. Baer et al., "XPS guide: Charge neutralization and binding energy referencing for insulating samples", J. Vac. Sci. Technol. A 38, 031204 (2020). [abs; DOI not checked]
29. ASTM E1523, Standard Guide to Charge Control and Charge Referencing Techniques in X-Ray Photoelectron Spectroscopy. [search snippet only]
30. G. Greczynski, L. Hultman, Prog. Mater. Sci. 107, 100591 (2020). [not read in this session; cited in the C0 plan]

---

## 未能取得出处的条目 / Items that could not be sourced

1. ~~IrO₂ 的 Ir 4d5/2 结合能与宽度~~ — **已解决 / resolved** (Freakley 2017 Table 2, see F1a).
2. **CasaXPS LF(α, β, w, m) 的数学定义，以及 LA 中 n 与高斯宽度的换算** / mathematical definition of CasaXPS LF(α, β, w, m), and the mapping from n to Gaussian width in LA. LA 的函数形式已取得（见 H 节）；LF 在 casaxps.com/manual.html 的全部文档中都没有。/ The LA functional form is obtained (section H); LF is absent from all documents at casaxps.com/manual.html. Freakley 的线型字符串已取得（F5a），但 PeakForge 要实现它需要 LF 的定义。Freakley 正文说定义在其补充材料里，但用户查过该文没有可下载的补充材料；所以只能从 CasaXPS 手册取，本次没有读到。/ The line-shape strings are obtained (F5a), but implementing them in PeakForge needs the LF definition. Freakley's text points to its Supporting Information, but the user found none available for download; it must come from the CasaXPS manual, which was not read.
3. **Kahk 2014 的屏蔽 / 未屏蔽组分的位置、面积、宽度、高斯/洛伦兹比** / Kahk 2014 screened / unscreened component positions, areas, widths, Gaussian/Lorentzian ratios. 正文没有数值，只在补充材料里（link.aps.org/supplemental/10.1103/PhysRevLett.112.117601）。这些是 6.5 keV 的数据，对 Al Kα 预设不是必需的。/ Not in the main text, only in the Supplemental Material. These are 6.5 keV data and are not required for an Al Kα preset.
4. **Scofield 1976 表中 1487 eV 的数值** / Scofield 1976 values at 1487 eV. 已用 1973 报告 1.5 keV 的值代替。/ Replaced by the 1973 report at 1.5 keV.
5. **KOH、K₂CO₃ 的 K 2p3/2** / K 2p3/2 in KOH and K₂CO₃.
6. **PTFE 的 C 1s = 292.48 eV（Beamson & Briggs）以及 Nafion、PTFE 的 C 1s、F 1s 半高宽** / PTFE C 1s = 292.48 eV (Beamson & Briggs) and FWHM of C 1s and F 1s in Nafion and PTFE.
7. ~~J. Phys. Chem. C 2024 关于 Nafion 样品 XPS 的内容~~ — **已解决 / resolved** (Dzara et al. 2024, see F1d and F6).
8. **766.2 eV 处 Co 俄歇峰的跃迁归属，以及它在 CoO、Co₃O₄、Co(OH)₂、CoOOH 中的位置** / transition assignment of the Co Auger peak at 766.2 eV and its position in the oxides and hydroxides.
9. **F KLL 的线宽与低结合能侧起始位置；一个本机 Co 2p 谱在 815 eV 处最大值的来源** / F KLL width and low-BE onset; origin of the 815 eV maximum in one Co 2p scan.
10. **Co 2p1/2 各多重态组分的参数** / component parameters for Co 2p1/2 multiplets. Biesinger 只给 2p3/2。/ Biesinger gives 2p3/2 only.
11. **Ta₂O₅ 的 O 2s 位置与宽度** / O 2s position and width in Ta₂O₅.
12. **Nafion、PTFE 的 F 2s 位置** / F 2s position in Nafion and PTFE.
13. **氧化态 Co 的 3p 结合能** / Co 3p BE in oxidised cobalt.
14. **Pfeifer 2016 表 3** / Pfeifer 2016 Table 3. 文本抽取无法对齐，未转录。/ Not transcribed; columns could not be aligned.
15. **除金属、IrO₂、无定形 IrOₓ 外其他 Ir 化合物的 4f7/2** / Ir 4f7/2 of Ir compounds other than the metal, IrO₂ and amorphous IrOₓ. 没有查。/ Not looked up.
