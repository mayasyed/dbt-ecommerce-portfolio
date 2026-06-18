# Experiment Design: Checkout Free Shipping Threshold Banner

**Project:** thelook_ecommerce A/B Test  
**Dataset:** `dbt-portfolio-498511.dbt_analytics`  
**Analyst:** Mahanoor Shams  
**Status:** Final  
**Date:** June 2026  

---

## Background

Checkout abandonment is one of the biggest revenue leaks in e-commerce. One of the most common nudges used to reduce it, and to lift basket size, is a dynamic banner showing the customer how close they are to qualifying for free shipping. This experiment tests whether adding a free shipping threshold banner to the checkout page raises average order value without causing customers to game the threshold by buying extra items they then return.

The dataset is `thelook_ecommerce`, a public BigQuery dataset simulating a fashion retailer. Because the dataset is static, this experiment follows a reconstruction design: the banner variant is simulated using a hash of `user_id`, and the resulting assignment is joined to actual order data. The analysis treats this as if the experiment were run prospectively.

---

## Hypothesis

Displaying a "Free shipping on orders over $50" banner at checkout will increase average order value compared to the standard checkout experience, because customers will add additional items to qualify for free shipping rather than pay a shipping fee.

We expect no meaningful increase in return rate. If return rate rises significantly in the treatment group, it would suggest customers are purchasing extra items they do not intend to keep, which would undermine the value of any AOV lift.

---

## Experiment Setup

| Parameter | Detail |
|---|---|
| Control | Standard checkout page, no shipping banner |
| Treatment | Checkout page with "Free shipping on orders over $50" banner |
| Assignment method | FARM_FINGERPRINT hash of `user_id`, split 50/50 using modulo 2 |
| Assignment unit | User, not session. Each user sees the same variant for the full test window |
| Scope | All users who place at least one order during the test period |

Assignment is handled by the dbt staging model `stg_experiment_assignments`. Any user who places more than one order during the test window is always assigned to the same variant, preventing crossover contamination.

Note: FARM_FINGERPRINT is used in place of MD5 because MD5 returns BYTES in BigQuery Standard SQL and cannot be used directly with MOD. FARM_FINGERPRINT returns INT64 and produces an equivalent even 50/50 split.

---

## Metrics

### Primary Metric: Average Order Value (AOV)

**Definition:** Total sale price across all items in a completed order, divided by the number of completed orders, grouped by variant.

**Direction:** Increase. The treatment group should produce a higher AOV than control.

**Baseline (from source data):**

```sql
select
    round(avg(order_value), 2) as baseline_aov,
    round(stddev(order_value), 2) as aov_stddev,
    count(*) as order_count
from (
    select
        order_id,
        sum(sale_price) as order_value
    from `bigquery-public-data.thelook_ecommerce.order_items`
    where status = 'Complete'
    group by order_id
)
```

**Result:** `baseline_aov` = $86.03, `aov_stddev` = $93.98, `order_count` = 31,144

### Guardrail Metric: Return Rate

**Definition:** The proportion of completed orders that are subsequently returned, grouped by variant.

**Direction:** No meaningful increase. If treatment return rate exceeds control by more than 3 percentage points, the experiment should be reviewed before any rollout decision is made.

**Baseline (from source data):**

```sql
select
    round(
        countif(status = 'Returned') / count(*),
        4
    ) as baseline_return_rate,
    count(*) as total_orders
from `bigquery-public-data.thelook_ecommerce.orders`
where status in ('Complete', 'Returned')
```

**Result:** `baseline_return_rate` = 28.6%, `total_orders` = 43,617

---

## Statistical Plan

### Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Significance level (alpha) | 0.05 | Standard threshold. One in 20 chance of a false positive |
| Statistical power (1 minus beta) | 0.80 | 80% chance of detecting a real effect if one exists |
| Test type | Two-tailed | Testing for any AOV difference, not assuming direction in advance |
| Statistical test | Welch t-test | Does not assume equal variance between variants, appropriate for order value data |

### Minimum Detectable Effect

A 5% relative lift in AOV is the minimum that would justify a full rollout. Lifts smaller than this would likely be outweighed by the ongoing cost of maintaining the banner in production.

| Estimate | Value | Source |
|---|---|---|
| Baseline AOV | $86.03 | BigQuery baseline query |
| MDE at 5% relative lift | $4.30 (absolute) | $86.03 × 0.05 |
| Standard deviation of order value | $93.98 | BigQuery baseline query |

### Sample Size Calculation

The formula for a two-sample t-test with equal group sizes:

```
n = 2σ² × (z_α/2 + z_β)² / δ²
```

Where:

- `σ` = standard deviation of AOV = $93.98
- `z_α/2` = 1.96 (alpha = 0.05, two-tailed)
- `z_β` = 0.84 (power = 0.80)
- `δ` = minimum detectable effect = $4.30

```
n = 2 × (93.98²) × (1.96 + 0.84)² / (4.30²)
n = 2 × 8,832.24 × 7.84 / 18.49
n ≈ 7,494 per variant
n ≈ 14,988 total
```

Verified using Python and statsmodels:

```python
from statsmodels.stats.power import TTestIndPower
import numpy as np

baseline_aov  = 86.03
aov_stddev    = 93.98
mde_absolute  = baseline_aov * 0.05   # $4.30
cohens_d      = mde_absolute / aov_stddev

analysis      = TTestIndPower()
n_per_variant = analysis.solve_power(
    effect_size = cohens_d,
    alpha       = 0.05,
    power       = 0.80,
    alternative = 'two-sided'
)

# Output: 7,494 per variant, 14,988 total
```

---

## Recommended Test Duration

**Daily order volume (from source data):**

```sql
select avg(daily_orders) as avg_daily_orders
from (
    select
        date(created_at) as order_date,
        count(distinct order_id) as daily_orders
    from `bigquery-public-data.thelook_ecommerce.orders`
    where status = 'Complete'
    group by 1
)
```

**Result:** `avg_daily_orders` = 12.39

Applying the duration formula:

```
days_required = n_per_variant / (avg_daily_orders × 0.50)
days_required = 7,494 / (12.39 × 0.50)
days_required ≈ 1,210 days
```

**Key finding:** At this dataset's traffic volume, detecting a 5% AOV lift with 80% power would require approximately 1,210 days (around 3.3 years). This is not feasible as a live experiment.

This finding highlights a fundamental constraint of A/B testing: statistical power requires sufficient traffic. The combination of low daily order volume (~12 orders per day), a high standard deviation ($93.98, which is larger than the mean AOV of $86.03), and a small target effect (5%) makes the required sample size very large.

In a real production e-commerce environment with thousands of daily orders, this test would be practical. For this portfolio project, the simulation approach resolves the constraint: by using four years of historical data as the observation window, the full sample size of 14,988 orders is already available in the dataset without waiting for live traffic.

This limitation is documented transparently as it reflects genuine analytical thinking: running the power calculation with real data before starting the analysis, rather than proceeding without checking feasibility.

---

## Success and Failure Criteria

| Outcome | Criteria | Decision |
|---|---|---|
| Clear win | AOV lift is statistically significant (p < 0.05) and at least 5% relative | Roll out to 100% of users |
| Inconclusive | No statistically significant AOV difference | Extend the test or investigate banner visibility |
| Guardrail breach | Treatment return rate exceeds control by more than 3 percentage points | Pause and investigate before making any rollout decision |
| Clear loss | Treatment AOV is significantly lower than control | Do not roll out. Investigate whether the banner created friction |

---

## Risks and Assumptions

**Novelty effect.** Users may interact with the banner differently in the first few days simply because it is unfamiliar. In a live experiment, running for at least 4 weeks mitigates this. In this simulation, the observation window spans multiple years, which largely eliminates this concern.

**Assignment leakage.** A user could technically be assigned to both variants if they log in from different accounts or clear cookies. The hash approach on `user_id` reduces but does not eliminate this. For this portfolio project, leakage is assumed to be negligible.

**Seasonality.** The thelook_ecommerce dataset spans several years. The test window used in the simulation (2024-01-01 to 2024-01-28) was chosen to avoid atypically high or low-traffic periods, to avoid confounding the results.

**Return rate lag.** Returns may take days or weeks to appear in the data after a purchase. In a live experiment, the return rate analysis should be run with a trailing observation window of at least 30 days after the test closes. In this simulation, the full return history is available in the dataset.

**Shipping threshold design.** This design assumes a flat $50 threshold and a single static banner. A more sophisticated version of this experiment might test a dynamic banner showing the customer their specific remaining amount to qualify. That is out of scope here but noted as a natural next iteration.

---

*This document was written before the simulation data was generated and serves as the pre-registered design for the experiment analysis. All baseline figures have been confirmed against the source data.*
