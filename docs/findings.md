# Findings

[Back to index](index.md)

## Key Correlations (Spearman)

Analysis of 98,000+ readings from the primary bedroom sensor reveals five notable metric relationships:

| Pair | rho | Direction | Interpretation |
|------|-----|-----------|----------------|
| Indoor PM2.5 <-> Filter Efficiency | -0.96 | Inverse | Near-perfect: validates that efficiency measurement works |
| CO2 <-> VOC | 0.65 | Positive | Both rise with low ventilation — when ERV flow is insufficient, CO2 and VOC accumulate together |
| Outdoor PM2.5 <-> Indoor Radon | 0.59 | Positive | Atmospheric stagnation drives both — still air traps radon indoors and particles outdoors |
| Outdoor Temp <-> Outdoor CO2 | -0.59 | Inverse | Winter inversions trap CO2 near ground level |
| Outdoor VOC <-> Outdoor NOX | -0.45 | Inverse | Different sources, opposite seasonality (VOC peaks summer, NOX peaks winter) |

### Why These Matter

**PM2.5 <-> Filter Efficiency (rho = -0.96)**: A strong inverse correlation is expected here because Indoor PM2.5 is a component of the efficiency formula (`Efficiency = (Outdoor - Indoor) / Outdoor`). The correlation doesn't independently "prove" the filter works — it confirms that the sensors produce consistent readings and the formula behaves as designed. A *weak* correlation would indicate sensor unreliability or confounding indoor sources overwhelming the measurement.

**CO2 <-> VOC (rho = 0.65)**: Both are ventilation indicators. When CO2 is high, VOC is too — confirming that the ERV is the primary ventilation mechanism and its flow rate drives both metrics simultaneously.

**Outdoor PM2.5 <-> Radon (rho = 0.59)**: This was unexpected. Radon is a soil gas, PM2.5 comes from combustion and natural sources. The connection is atmospheric stagnation: when there's no wind and a temperature inversion, outdoor particles can't disperse AND indoor radon can't ventilate. Both rise together.

## Filter Longevity

MERV 13 filters maintain >85% efficiency for 120+ days. The manufacturer-recommended replacement interval is 45 days.

### Data-Driven Evidence

- Average efficiency over the measurement period: consistently above 85%
- A filter at 197% of theoretical "max life" was still performing at 87.3% efficiency
- Load-based prediction models failed — filter load doesn't correlate with efficiency degradation

### Caveats

- **Outdoor PM2.5 threshold**: The efficiency formula is unreliable when outdoor PM2.5 is below ~5 ug/m3 (see [Methodology — Filter Efficiency Formula](methodology.md#filter-efficiency-formula)). Days with very clean outdoor air are excluded from efficiency tracking. If a significant portion of the 120+ day window had low outdoor PM2.5, fewer days contributed to the efficiency measurement than the calendar count implies.
- **Single household**: These results reflect one home's HVAC system, climate zone, and occupancy patterns. Filter longevity depends on factors like outdoor pollution levels, home size, duct configuration, and ERV usage.

### Cost Impact

Replacing filters every 45 days costs $130-$910/year depending on filter quality. Data-driven replacement at 120+ days reduces this by 60-70% without compromising air quality.

### Why Manufacturer Specs Are Conservative

Manufacturers optimize for liability, not for your specific conditions:
- They assume worst-case particulate loads (dusty construction areas)
- They can't know your outdoor air quality
- A failed filter is a warranty claim; an over-replaced filter is revenue

## The ERV Tradeoff

An Energy Recovery Ventilator (ERV) exchanges stale indoor air for fresh outdoor air while recovering heat. This creates a fundamental tradeoff:

**More ventilation (higher ERV flow)**:
- Lower CO2 (fresh air dilutes CO2)
- Lower VOC (fresh air dilutes volatile organics)
- Higher indoor PM2.5 (outdoor particles bypass the main filter)

**Less ventilation (lower ERV flow)**:
- Higher CO2 (occupant breathing accumulates)
- Higher VOC (off-gassing from furniture, cleaning products)
- Lower indoor PM2.5 (main MERV 13 filter handles recirculated air)

The dashboard's ERV Tradeoff page visualizes this with a dual-axis chart: CO2 and PM2.5 on the same timeline, showing the inverse relationship during ventilation changes.

### Practical Decision

The data suggests prioritizing CO2 and VOC reduction (more ventilation) when:
- Outdoor PM2.5 < 15 ug/m3
- Outdoor NOX is low (no nearby traffic or industrial activity)

Reduce ventilation when:
- Outdoor PM2.5 > 20 ug/m3 (wildfire smoke, high pollution days)
- Outdoor VOC/NOX elevated (traffic, industrial activity)

## Atmospheric Stagnation Pattern

The PM2.5-Radon correlation (rho = 0.59) reveals a weather-driven pattern:

1. Temperature inversions (common in winter) trap cold air near the ground
2. Without vertical mixing, outdoor PM2.5 cannot disperse
3. Simultaneously, radon gas from soil cannot ventilate and accumulates indoors
4. Both metrics rise together, even though they have completely different sources

This pattern is visible in the heatmaps as multi-day bands of elevated readings, typically in December-February.

## Seasonal Patterns

### Winter (Dec-Feb)
- Higher outdoor CO2 (temperature inversions)
- Higher indoor CO2 (windows sealed, less natural ventilation)
- Higher radon (atmospheric stagnation)
- Higher outdoor PM2.5 (inversions + heating emissions)

### Summer (Jun-Aug)
- Lower outdoor CO2 (good atmospheric mixing)
- Lower indoor CO2 (windows open, natural ventilation)
- Lower radon (ventilation carries radon out)
- Variable outdoor PM2.5 (wildfire risk offsets generally cleaner air)
