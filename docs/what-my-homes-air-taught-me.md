# What my home's air taught me

Someone I loved lived 20 years next to a freeway. I wanted to understand what that meant for the people I love now.

The trigger was more mundane. A few years ago my gas furnace kept tripping its overheat-safety cutoff. My CO2 sensor was reading unusually high at the same time. An HVAC company came out and found that a previous installer had clamped the air duct leading to my room — the airflow problem was causing both the overheating and the bad air exchange. I was mad enough to scrap the furnace and replace it with a heat pump and an ERV. The continuous monitoring system grew out of wanting a signal I could trust the next time a human told me *"it's fine."*

I work from home in a condo finished in early 2020 — airtight by modern energy code, which is great for utility bills and difficult for keeping air actually fresh behind a closed door. And with a kid whose asthma rules out the cheap "open a window" fix, we couldn't just let the seal leak. Nine months of continuous measurement later — three sensors, 142,000 readings across indoor PM2.5, CO2, VOCs, radon, outdoor PM2.5, temperature, and humidity — here's what the data actually says.

None of this is original science. It's what happens when you take a single home seriously as a measurement site instead of trusting the labels on the filters or the installer's word.

---

## Four findings from nine months

### 1. Your bedroom CO2 is probably above 1,000 ppm overnight

Two people in a closed bedroom with the door shut can push CO2 from a ~420 ppm outdoor baseline to 2,000–3,000 ppm by morning in a tight room. That's the signal the room isn't exchanging outdoor air overnight — so occupant-generated pollutants (exhaled CO2, bioeffluents, humidity) are accumulating alongside. You don't have to trust my data: buy an ~$80 CO2 monitor (Aranet4, Airthings, anything that reads NDIR), put it on the nightstand of a bedroom where the door stays shut, wake up and look at the number.

The measurement insight on top of that: in my data, indoor CO2 and indoor VOCs correlate at ρ = 0.65. Both rise together when ERV flow is insufficient, because in this house the VOCs are predominantly occupant/activity-sourced rather than material-off-gassed. That correlation isn't universal — homes with heavy new-material off-gassing produce VOCs independent of ventilation, breaking the pairing — but in a household like mine, an inexpensive CO2 monitor has served as a reasonable under-ventilation proxy for VOCs too. Not a canary for every indoor pollutant. A canary for the ones your family makes.

### 2. An installer substitution the sensors caught before we did

For six weeks in September-October 2025, my OEM-specified ERV filter was temporarily replaced with a generic MERV-13-rated HVAC-style panel filter of a different form factor — a substitution made during a service visit that a human trusting the "it's MERV 13, same thing" assurance would have accepted. Same home, same HVAC, same outdoor air, same sensors. Only the filter changed.

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

- **France, 1982** (Arrêté du 24 mars 1982): mandated general, permanent, swept-airflow ventilation with minimum extraction flow rates in all residences. The regulation itself is technology-neutral — but the flow-rate requirements drove near-universal adoption of mechanical ventilation (VMC) in practice. Required A+ to C emissions labeling on building materials since 2012.
- **Japan, 2003**: after the nationwide "Sick House Syndrome" crisis, the Building Standards Law was amended to require mechanical ventilation delivering at least 0.5 ACH in residential rooms, typically implemented as 24-hour ventilation.
- **Norway, TEK17 §13-2**: performance-based residential ventilation — at least 1.2 m³/h per m² of floor area while occupied, 26 m³/h per planned bed in bedrooms, extraction from kitchen/bath/toilet. Balanced mechanical ventilation with heat recovery is the practical way to meet both this and the chapter 14 energy rules; F7 (~MERV 13) supply-air filtration is recommended in separate Arbeidstilsynet workplace-air guidance rather than TEK17 itself.
- **Germany, GEG §6 + DIN 1946-6**: every new or renovated dwelling requires a Lüftungskonzept (ventilation concept). The legal duty is in the Gebäudeenergiegesetz; DIN 1946-6 is the recognised engineering standard for satisfying it.

**The US gap is specifically on filtration, not on whether mechanical ventilation is required.** ASHRAE 62.2 sets performance-based airflow requirements (roughly ~90 CFM continuous for a 2,000 ft² / 3-bedroom home — about 30–50% less than Norway's 1.2 m³/h per m² for the same house) and prescribes a **MERV 6 minimum** on ducted systems. MERV 6 catches dust, pollen, and larger debris but not the sub-micron combustion particles that dominate near-road PM2.5 or wildfire smoke. A growing number of states (California Title 24 since 2013, others since) have raised their residential minimum to MERV 13 in new construction; most have not. There is no federal VOC emissions labeling on building materials and no federal indoor CO2 target.

The three-layer retrofit I have — air-sealing, ERV with MERV 13 supply filtration, MERV 13 HVAC recirculation — is a ~$3,000 DIY approximation of what Norwegian, Japanese, French, and German families get by default from the building code. The technology is not new. The science is not disputed. The gap is regulatory.

For the full policy and research comparison: [The Freeway Air Problem](https://github.com/minghsuy/hvac-air-quality-analysis/wiki/The-Freeway-Air-Problem).

---

## The system is still running

This isn't a study I finished. The monitoring is live. [HVACMonitor v3](https://github.com/minghsuy/hvac-air-quality-analysis/blob/main/HVACMonitor_v3.gs) — a Google Apps Script — runs on an hourly trigger against the Sheet that holds the raw sensor rows, re-calibrates efficiency thresholds seasonally from the actual distribution of the house's data, and emails me when efficiency, CO2, PM2.5, or radon drifts outside confidence bands. Alerts are escalation-based: WARNING on first deviation, CRITICAL on sustained deviation, with a cooldown so a single noisy reading doesn't wake the house at 3 AM.

Three real incidents the system has caught:

- **Before the measurement system existed (origin):** clamped duct + overheat cutoff + elevated CO2 — the catalyst for scrapping the furnace and building continuous monitoring.
- **Sept 6 – Oct 15, 2025:** installer substituted a generic MERV-13-labeled filter during a service visit. Efficiency drop detected on the first day of data; confirmed across 40 days of operation.
- **Feb 7–8, 2026:** in-service filter degradation. WARNING → CRITICAL escalation over 8 hours. The family smelled the air before the human interpretation caught up to the numbers.

The next failure — whatever form it takes — gets caught the same way. The point of building this was never the nine months of receipts behind this page. It's the next nine months, and the nine after that.

---

## What you can actually do this week

1. **Buy a CO2 monitor** (~$80, Aranet4 or similar). Put it in the bedroom where the people you most care about sleep. Check it at 6am. This is the cheapest, most visceral conversion from "air quality is abstract" to "oh, that's what 1,800 ppm feels like."
2. **Check what MERV rating your current HVAC filter is.** The label on the filter itself will say. MERV 6 and MERV 8 are the common federal / IRC minimums — fine for protecting the blower and catching larger dust and pollen, but they don't meaningfully reduce PM2.5 or combustion particles. MERV 13 is the threshold where sub-micron filtration starts. If you want to swap up: ECM blower motors can almost always handle a 1" MERV 13 pressure drop; PSC motors should check first, and 4–5" deep-media MERV 13 cartridges keep the pressure drop close to what a 1" MERV 8 imposes.
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
