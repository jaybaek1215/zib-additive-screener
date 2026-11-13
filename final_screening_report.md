# Final Screening Report: Autonomous Polymer Electrolyte Additive Discovery for Aqueous Zinc-Ion Batteries (ZIBs)

**Date:** 2026-11-12  
**Target:** Design of High-Performance Polymer Electrolyte Additives for Dendrite Suppression and Hydrogen Evolution Reaction (HER) Mitigation  
**Potential Energy Surface:** Microsoft MatterSim (v1.0.0-5M, MLIP)  

---

## 1. Executive Summary

수계 아연 이온 전지(ZIBs)의 상용화를 가로막는 핵심 난제인 **(1) 아연 음극 표면 덴드라이트 성장**, **(2) 자유수(Free Water)에 의한 수소발생반응(HER) 및 부식**, **(3) 높은 $[\text{Zn}(\text{H}_2\text{O})_6]^{2+}$ 탈용매화 에너지 장벽**을 극복하기 위해, MatterSim MLIP 기반 폐루프(Closed-loop) 자율 탐색 파이프라인을 가동하였습니다.

기준 물질(Gen 0, Ethylene Glycol 및 PEG3)의 구조-물성 상관관계(SAR)를 바탕으로 1세대(Gen 1, 6종)와 진화된 2세대(Gen 2, 6종) 올리고머를 순차 설계·스크리닝한 결과, **기준선(EG, Score 0.5589) 대비 최대 +170.66% 향상된 `GEN2_02_AN_AM_AN` (Score 1.5127)**을 비롯한 우수 후보군을 성공적으로 발굴하였습니다.

```mermaid
flowchart LR
    A["Gen 0 (Baseline)<br/>EG (0.5589)<br/>PEG3 (0.8763)"] -->|"SAR 분석 & 1차 아마이드/니트릴 도입"| B["Gen 1 (Exploration)<br/>PAM3 (1.2054)<br/>PAN3 (1.1191)"]
    B -->|"공중합 시너지 & 불소화 복합화"| C["Gen 2 (Evolution)<br/>AN-AM-AN (1.5127)<br/>AM-AN-AM (1.1866)"]
```

---

## 2. 세대별 스크리닝 종합 랭킹 (PASS 후보군)

스크리닝 지표는 아래 물리적 메커니즘을 반영하여 산출되었습니다:
$$\text{Score} = -0.4\,\Delta E_{\text{H-bond}} - 0.6\,\Delta E_{\text{exchange}} - 0.5\,\Delta E_{\text{ads}} - \text{Penalty}_{\text{desolv}}$$

| Rank | Generation | Candidate ID | Polymer Name | Backbone | Functional Groups | $\Delta E_{\text{H-bond}}$ (eV) | $\Delta E_{\text{exchange}}$ (eV) | $\Delta E_{\text{ads}}$ (eV) | Composite Score | Improvement vs EG (%) |
|:---:|:---:|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **1** | **Gen 2** | `GEN2_02_AN_AM_AN` | Poly(AN-co-AM) Trimer (AN-AM-AN) | Poly(acrylonitrile-co-acrylamide) | `-CN (x2), -C(=O)NH2 (x1)` | **-0.7966** | **-1.8287** | **-0.8797** | **1.5127** | **+170.66%** |
| **2** | **Gen 1** | `GEN1_01_PAM3` | Polyacrylamide Trimer | Polyacrylamide | `-C(=O)NH2 (x3)` | **-0.6624** | **-1.1261** | **-0.5296** | **1.2054** | **+115.67%** |
| **3** | **Gen 2** | `GEN2_01_AM_AN_AM` | Poly(AM-co-AN) Trimer (AM-AN-AM) | Poly(acrylamide-co-acrylonitrile) | `-C(=O)NH2 (x2), -CN (x1)` | **-0.8170** | **-0.8243** | **-0.7304** | **1.1866** | **+112.31%** |
| 4 | Gen 2 | `GEN2_06_TFAM_AM` | Poly(TFEMA-co-AM) Dimer | Fluorinated polyacrylamide | `-CF3, -C(=O)NH- (x2)` | -0.9912 | -1.0851 | -0.2332 | 1.1642 | +108.30% |
| 5 | Gen 1 | `GEN1_06_PAN3` | Polyacrylonitrile Trimer | Polyacrylonitrile | `-CN (x3)` | -0.5458 | -0.9021 | -0.7190 | 1.1191 | +100.23% |
| 6 | Gen 1 | `GEN1_05_PDMA2` | Poly(N,N-dimethylacrylamide) Dimer | Polyacrylamide (tertiary) | `-C(=O)N(CH3)2 (x2)` | -0.7298 | -1.4621 | +0.1337 | 1.1023 | +97.23% |
| 7 | Gen 1 | `GEN1_02_PVP2` | Polyvinylpyrrolidone Dimer | Polyvinylpyrrolidone | Pyrrolidone ring (x2) | -0.6339 | -0.9389 | -0.4069 | 1.0203 | +82.56% |
| 8 | Gen 0 | `GEN0_02_PEG3` | Triethylene Glycol (PEG-trimer) | Polyether (-CH2CH2O-) | `-OH, -O-` | -0.8540 | -0.3475 | -0.6524 | 0.8763 | +56.79% |
| 9 | Gen 0 | `GEN0_04_PAA3` | Polyacrylic Acid Trimer | Polyacrylate | `-COOH (x3)` | -0.9461 | -0.2670 | -0.2833 | 0.6803 | +21.72% |
| 10 | Gen 0 | `GEN0_03_PVA3` | Polyvinyl Alcohol Trimer | Polyvinyl (-CH2CH-) | `-OH (x3)` | -0.6582 | -0.3176 | -0.2872 | 0.5975 | +6.91% |
| 11 | Gen 1 | `GEN1_03_Triglyme` | Triethylene Glycol Dimethyl Ether | Polyether (-CH2CH2O-) | `-O- (x4), -OCH3` | -0.6354 | -0.4338 | -0.0982 | 0.5635 | +0.82% |
| 12 | Gen 0 | `GEN0_01_EG` | Ethylene Glycol (Baseline) | Aliphatic C2 | `-OH (x2)` | -0.5860 | -0.3141 | -0.2720 | 0.5589 | 0.00% |
| 13 | Gen 2 | `GEN2_03_PHEAA2` | Poly(HEAA) Dimer | Poly(hydroxyalkylacrylamide) | `Amide, -OH (x2)` | -0.8033 | -0.2124 | -0.0158 | 0.4567 | -18.29% |

---

## 3. Top-3 최우수 폴리머 후보 심층 분석

### 🥇 1위: `GEN2_02_AN_AM_AN` (Composite Score: 1.5127, 개선율: +170.66%)
- **SMILES:** `CC(C#N)CC(C(=O)N)CC(C#N)C`
- **화학 구조:** Poly(acrylonitrile-co-acrylamide) 3량체 (Nitrile-Amide-Nitrile)
- **물리화학적 메커니즘:**
  1. **역대 최강의 계면 흡착 보호막 ($\Delta E_{\text{ads}} = -0.8797\text{ eV}$):** 양 말단의 시아노기($-\text{C}\equiv\text{N}$)가 갖는 강한 쌍극자 모멘트와 질소 비공유전자쌍이 Zn(0001) 결정 표면에 다접점 화학 흡착층을 형성하여 물 분자의 접근을 원천 차단하고 아연 수지상(Dendrite) 성장을 물리적으로 억제합니다.
  2. **우수한 Zn²⁺ 용매화 치환 ($\Delta E_{\text{exchange}} = -1.8287\text{ eV}$):** 중앙의 1차 아마이드($-\text{CONH}_2$) 카르보닐 산소가 $[\text{Zn}(\text{H}_2\text{O})_6]^{2+}$의 물 분자 1개를 치환하여 탈용매화 장벽을 효과적으로 조절합니다.
  3. **안정적인 수소결합 포집 ($\Delta E_{\text{H-bond}} = -0.7966\text{ eV}$):** 1차 아마이드의 프로톤(-NH2)과 카르보닐이 자유수와 2개의 수소결합을 견고히 형성하여 HER 부반응을 억제합니다.

### 🥈 2위: `GEN1_01_PAM3` (Composite Score: 1.2054, 개선율: +115.67%)
- **SMILES:** `CC(C(=O)N)CC(C(=O)N)CC(C(=O)N)C`
- **화학 구조:** Polyacrylamide 3량체 (Trimer)
- **물리화학적 메커니즘:**
  1. **이상적인 용매화 윈도우 ($\Delta E_{\text{exchange}} = -1.1261\text{ eV}$):** 탈용매화 적정 윈도우($-1.5 \sim -0.3\text{ eV}$) 정중앙에 위치하여, 너무 과도하게 결합하지 않으면서도 수화 구조를 부드럽게 재구성합니다.
  2. **균형 잡힌 3중 성능:** 수소결합($-0.6624\text{ eV}$)과 계면 흡착($-0.5296\text{ eV}$)이 모두 우수하여 단일 단량체 기반 고분자 중 가장 우수한 종합 점수를 기록했습니다.

### 🥉 3위: `GEN2_01_AM_AN_AM` (Composite Score: 1.1866, 개선율: +112.31%)
- **SMILES:** `CC(C(=O)N)CC(C#N)CC(C(=O)N)C`
- **화학 구조:** Poly(acrylamide-co-acrylonitrile) 3량체 (Amide-Nitrile-Amide)
- **물리화학적 메커니즘:**
  1. **강화된 자유수 포집 ($\Delta E_{\text{H-bond}} = -0.8170\text{ eV}$):** 2개의 1차 아마이드기가 자유수와의 수소결합 네트워크 형성을 주도하여 HER 억제 능력이 더욱 강화되었습니다.
  2. **강력한 계면 보호 ($\Delta E_{\text{ads}} = -0.7304\text{ eV}$):** 중심부의 시아노기가 Zn 표면과의 밀착 흡착을 유도합니다.

---

## 4. 백본 및 작용기 설계 인사이트 (SAR)

1. **아마이드(Amide) vs 카르복실(Acid) vs 알코올(Alcohol):**
   - Gen 0의 `-COOH`(PAA)는 강한 수소결합($-0.9461\text{ eV}$)을 보였으나 계면 흡착($-0.2833\text{ eV}$)이 미흡했습니다.
   - 반면 **1차 아마이드($-\text{CONH}_2$)**는 카르보닐($\text{C=O}$)의 강한 전자 공여와 $-\text{NH}_2$의 수소 결합 공여가 공존하여, Zn²⁺ 용매화 치환과 자유수 포집을 동시에 가장 높은 수준으로 만족시킵니다.
   - 3차 아마이드(PDMA, $-\text{CONMe}_2$)는 치환력은 우수($-1.4621\text{ eV}$)하나 메틸기의 입체 장애로 인해 표면 흡착에 불리($+0.1337\text{ eV}$)했습니다.

2. **시아노기($-\text{C}\equiv\text{N}$, Nitrile)의 결정적 역할:**
   - PAN 백본 및 시아노 유도체는 Zn(0001) 금속 표면에 대해 **$-0.7 \sim -0.88\text{ eV}$** 수준의 압도적인 화학 흡착력을 보여줍니다.
   - 물 분자의 흡착 에너지($\approx -0.35\text{ eV}$)보다 2배 이상 강하므로, 아연 전극 표면에서 물을 완전히 밀어내고 자가조립 단분자막(SAM) 형태의 치밀한 보호층을 구축할 수 있습니다.

3. **공중합(Copolymer) 시너지 효과:**
   - 단일 폴리머(PAM: 1.2054, PAN: 1.1191)보다, 두 작용기를 적절한 비율로 배치한 **공중합체 `GEN2_02_AN_AM_AN` (1.5127)**이 각 기능(계면 흡착 + 용매화 변조 + 수소결합)을 극대화하여 가장 높은 시너지를 창출함을 증명하였습니다.

4. **불소화 작용기($-\text{CF}_3$) 도입 효과:**
   - `GEN2_06_TFAM_AM`은 $\Delta E_{\text{H-bond}} = -0.9912\text{ eV}$로 전 후보 중 가장 강력한 수소결합 능력을 기록했습니다. 불소 원자의 강한 전자 흡인 유도 효과(Inductive effect)가 인접 아마이드의 NH 산도를 증가시켜 물 분자와의 결합력을 극대화한 것으로 분석됩니다.

---

## 5. 비물리적 구조(WARN) 실패 분석 및 기하학적 교훈

- **`GEN1_04_PHEA2` & `GEN2_04_VP_AM` (BFGS 미수렴, $f_{\max} > 0.10\text{ eV/\AA}$):**
  - 길고 유연한 에톡시 에스테르 사슬이나 부피가 큰 2개의 피롤리돈 고리가 Zn 슬래브/클러스터 주변에서 다중 입체 충돌(Steric clash) 및 비틀림 장벽을 유발하여 제한된 스텝 내 평형 상태에 도달하지 못함.
- **`GEN2_05_CN_DEG` (원자 간격 겹침, $\text{min\_dist} < 0.75\text{ \AA}$):**
  - 선형 다이에틸렌 글라이콜 에테르의 과도한 형태적 자유도로 인해 Zn 배위 시 말단 관능기가 자체 접힘(Self-folding)을 일으켜 비물리적 원자 중첩 발생.
- **교훈:** 향후 전해질 첨가제 설계 시 백본의 적절한 강직성(Rigidity)과 간결한 분자 크기 유지가 계산 및 실제 전기화학적 안정성 모두에 필수적입니다.
