# What my home's air taught me

Someone I loved lived 20 years next to a freeway. I wanted to understand what that meant for the people I love now. Nine months of continuous measurement later — three sensors, 142,000 readings across indoor PM2.5, CO2, VOCs, radon, outdoor PM2.5, temperature, and humidity — here's what the data actually says.

None of this is original science. It's what happens when you take a single home seriously as a measurement site instead of trusting the labels on the filters.

---

## Four findings from nine months

### 1. Your bedroom CO2 is probably above 1,000 ppm overnight

Two people in a closed bedroom with the door shut can push CO2 from an outdoor baseline of ~420 ppm to 2,000–3,000 ppm by morning. The [Harvard COgFx study (Allen et al. 2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4892924/) reported ~50% drops in crisis-response and information-usage scores between 550 and 1,400 ppm. That specific finding has been partially contested since — [Scully et al. 2019](https://pubmed.ncbi.nlm.nih.gov/30975324/) found no cognitive decrement up to 2,500 ppm in controlled submariner conditions, and subsequent meta-analyses suggest pure-CO2 effects are smaller than the original paper implied. What is NOT contested: elevated overnight CO2 is a reliable proxy for under-ventilation, which also means accumulating VOCs, bioeffluents, and particulates. Most US residential code has no indoor CO2 target. France, Germany, and Norway cap at ~1,000 ppm in their residential ventilation codes.

You don't have to trust my data. Buy an ~$80 CO2 monitor (Aranet4, Airthings, anything that reads NDIR), put it on the nightstand, wake up and look at the number.

The measurement insight on top of that: in my data, indoor CO2 and indoor VOCs correlate at ρ = 0.65. Both are ventilation-limited signals — when the ERV flow is insufficient, both rise together. Which means **an inexpensive CO2 monitor doubles as an under-ventilation proxy for VOCs.** You don't need a VOC sensor to know the air is stale. CO2 is the canary.

### 2. Two filters with the same "MERV 13" rating differed by 24 percentage points

For six weeks in September-October 2025, my OEM-specified ERV filter was temporarily replaced with a generic MERV-13-rated HVAC-style panel filter of a different form factor. Same home, same HVAC, same outdoor air, same sensors. Only the filter changed.

Measured indoor PM2.5 filtration efficiency:
- OEM MERV 13: ~95% median (higher, but partly limited by sensor resolution — see caveats)
- Generic MERV-13-rated substitute: **69% median**, worst days down to 35-50%
- The moment the OEM filter was reinstalled: back to 95%+ on day one

**"MERV 13" is a rating, not a performance guarantee.** Two filters carrying the same label can differ by 20+ points in real-world efficiency in the same installation. The ASHRAE 52.2 test protocol defines minimum particle-capture rates at specific sizes under controlled dust loading — two filters barely passing the threshold vs. comfortably exceeding it can both claim MERV 13. The media, the pleat density, the housing fit all vary.

The only way to tell which one you actually have is to measure.

→ [Interactive chart and full cycle-by-cycle data](reports/findings.html#filter-cycles)

### 3. Most households replace filters too early. The one real failure in nine months got caught by monitoring, not the calendar

Manufacturers optimize replacement schedules for the dirtiest household they'll ever encounter — plus liability padding. A 45- or 90-day schedule guarantees 100% of households stay safe, which means the typical household is over-replacing.

My monitoring system caught exactly one genuine filter failure in nine months of data. On Feb 7–8, 2026, hourly master-bedroom filter efficiency dropped from a ~95% baseline to **49% by 9am Feb 8**. The system escalated from WARNING to CRITICAL. The family could smell it — a musty quality to the air — before replacement. After the new filter: efficiency back to 100% within an hour.

For this household at current filter prices ($100 per OEM ERV MERV 13), the measured ERV life of 116–151 days vs. the manufacturer's 90 days translates to **~$130/year saved on that one filter.** The main 4" return filter is harder — there's no indoor-only sensor downstream of it, so I can't measure its efficiency in isolation and still replace it on a conservative 6-month interval. The zone filters are $10 each on a fixed 90-day schedule — not worth measuring.

**Savings scale with filter price, not filter count.** A household running premium $200–300 MERV 13 filters saves 2–3× more per filter than this one. The ~$200 outdoor-sensor hardware pays back in about 1.5 years at my prices; faster for more expensive filter setups. See [findings.md § Cost Impact](findings.md#cost-impact) for the full per-filter table.

→ [Hour-by-hour chart of the Feb 7-8 alert escalation](reports/findings.html#feb-case)

### 4. US residential ventilation code is 43 years behind France

This part is not about my house. It's about why my house is the way it is.

- **France, 1982**: mandated continuous mechanical exhaust ventilation in all residences. Required emissions labeling on building materials (A+ through C) since 2012.
- **Japan, 2003**: after the nationwide "Sick House Syndrome" crisis, mandated 24-hour continuous mechanical ventilation in every new residence. Banned chlorpyrifos in building materials outright.
- **Norway, TEK17**: balanced mechanical ventilation with heat recovery in every dwelling. Airtightness ≤1.5 ACH50. Supply air filtration at F7 (~MERV 13) from the factory. Indoor CO2 target around 920 ppm.
- **Germany, DIN 1946-6 / GEG**: every new or renovated dwelling requires a ventilation concept. Airtightness testing required. Indoor CO2 target of 1,000 ppm codified.

**The US has no federal residential indoor air quality standard.** The minimum required HVAC filtration in ASHRAE 62.2 is MERV 6 — catches dust bunnies and essentially nothing of combustion-particle or wildfire-smoke consequence. No federal indoor CO2 target. No VOC emissions labeling on building materials. No airtightness requirement comparable to European codes. California leads among US states (Title 24 requires mechanical ventilation since 2013) but its airtightness threshold is far more lenient than Norway's.

The three-layer retrofit I have — air-sealing, ERV with MERV 13 supply filtration, MERV 13 HVAC recirculation — is a ~$3,000 DIY approximation of what Norwegian, Japanese, French, and German families get by default from the building code. The technology is not new. The science is not disputed. The gap is regulatory.

For the full policy and research comparison: [The Freeway Air Problem](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/The-Freeway-Air-Problem).

---

## What you can actually do this week

1. **Buy a CO2 monitor** (~$80, Aranet4 or similar). Put it in the bedroom where the people you most care about sleep. Check it at 6am. This is the cheapest, most visceral conversion from "air quality is abstract" to "oh, that's what 1,800 ppm feels like."
2. **Check what MERV rating your current HVAC filter is.** The label on the filter itself will say. If it's MERV 6 or MERV 8, that's the US code minimum — it catches almost nothing of consequence for traffic emissions or wildfire smoke. Swap to MERV 13 if your blower motor can handle the pressure drop (ECM motors: almost always yes; PSC motors: check first, 4-5" media filters keep the pressure drop low).
3. **If you live within 500 meters of a freeway**, the [California Air Resources Board research](https://ww2.arb.ca.gov/news/air-resources-board-approves-land-use-planning-handbook) puts your background PM2.5 at 45-95% above urban baseline. A MERV 13 filter and a sealed building envelope matter more for you than for most.

---

## Caveats

- **Single household, nine months**: these results are not generalizable to other homes or climates. They are useful as measurement methodology — and as counterexamples to specific manufacturer claims (one filter at 197% of its theoretical "max life" still at 87.3% efficiency falsifies "load predicts degradation" as a universal claim).
- **No reference-instrument co-location**: I used consumer-grade sensors (Airthings View Plus, AirGradient Open Air & ONE). No calibration against a research-grade reference. Absolute PM2.5 accuracy is not claimed; the within-dataset relative dynamics are what the findings rest on.
- **Sensor precision**: the Airthings PM2.5 channel rounds to whole numbers. When true indoor PM is below 0.5 µg/m³, the reported efficiency hits 100% as a sensor-resolution artifact, not as a physics claim. The [evidence report](reports/findings.html) quantifies this per filter period (`indoor_zero_pct` column).
- **No health-outcome claims.** Someone in my household had a concurrent medical intervention during the measurement window that materially affects respiratory symptoms. I cannot attribute any change in anyone's health to the air quality work; it would be dishonest to. This is a measurement-methodology contribution, not a health-intervention study.

---

## Evidence and replication

- **[Interactive findings report](reports/findings.html)** — 142k-row dataset, per-cycle efficiency, Feb 7-8 case study, correlation matrix, full caveats.
- **[Technical findings](findings.md)** — numeric summary of all five Spearman correlations and the four filter periods.
- **[The Freeway Air Problem](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/The-Freeway-Air-Problem)** — the full research and policy deep-dive behind this page.
- **[Methodology](methodology.md)** — Spearman vs Pearson, LOWESS anomaly detection, seasonal thresholds, efficiency formula.
- **[GitHub repo](https://github.com/minghsuy/hvac-air-quality-analysis)** — everything is reproducible. `uv run python scripts/analysis/verify_findings.py` regenerates the evidence report.

---

*Nine months of data in one home is not proof. It's a measurement case study that says: the labels do not always tell the truth, the monitoring costs less than a round of filter replacements, and the code your builder followed is probably 40 years behind every other wealthy country. Each of those is easy to verify yourself.*
