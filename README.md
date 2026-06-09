# dbt E-commerce Analytics Portfolio

A dbt Core project demonstrating dimensional modelling and ELT data transformation using the `thelook_ecommerce` public dataset on Google BigQuery.

---

## Overview

This project builds a clean, tested dimensional model from raw e-commerce transactional data. Raw source tables from BigQuery's public dataset are transformed through a structured three-layer pipeline into analytics-ready fact and dimension tables.

The project demonstrates:

- Modular SQL transformation using dbt Core
- Dimensional modelling with fact and dimension tables
- Source freshness tracking and data quality testing
- Auto-generated documentation and lineage graphs
- Cloud-native execution on Google BigQuery

---

## Tech Stack

| Tool | Purpose |
|---|---|
| dbt Core 1.11 | Data transformation framework |
| Google BigQuery | Cloud data warehouse |
| thelook_ecommerce | Public source dataset |
| Python 3.12 | Runtime environment |
| Git | Version control |

---

## Data Architecture

The project follows a standard three-layer dbt architecture:

```
Sources (bigquery-public-data)
    └── Staging layer (views)       Clean and rename raw columns
            └── Marts layer (tables)    Final dimensional model
```

### Staging models (views)

One model per source table. Renames columns consistently, casts data types, and applies no business logic. Each staging model uses the `{{ source() }}` macro to reference raw data.

| Model | Source table | Description |
|---|---|---|
| stg_order_items | thelook_ecommerce.order_items | One row per item within an order |
| stg_orders | thelook_ecommerce.orders | One row per order header |
| stg_products | thelook_ecommerce.products | Product catalogue |
| stg_users | thelook_ecommerce.users | Customer records |

### Mart models (tables)

Final analytical tables built from staging models using `{{ ref() }}`. Configured as physical tables for BI performance.

| Model | Type | Rows | Description |
|---|---|---|---|
| fct_order_items | Fact table | 181k | One row per item sold. Grain: order item. Contains sale price and fulfilment timestamps. |
| dim_orders | Dimension | 125k | Order attributes including status, dates, and item count |
| dim_products | Dimension | 29k | Product attributes including brand, category, cost, and retail price |
| dim_users | Dimension | 100k | Customer attributes including age, gender, and geographic data |

---

## Lineage Graph

![Lineage graph](lineage.png)

The lineage graph shows the full dependency chain: raw source tables flow into staging models, which feed into the final mart layer. `stg_orders` is referenced by both `fct_order_items` and `dim_orders`, reflecting the join in the fact table SQL.

---

## Data Quality Tests

23 schema tests run across all 8 models using `dbt test`.

Tests applied:

- `not_null` on all primary keys and foreign keys
- `unique` on all primary keys

All 23 tests pass against the live dataset.

```
Done. PASS=23 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=23
```

---

## How to Run

### Prerequisites

- Python 3.12
- dbt BigQuery adapter: `pip install dbt-bigquery`
- Google Cloud account with BigQuery enabled
- gcloud CLI installed and authenticated:

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### Setup

1. Clone this repository:

```bash
git clone https://github.com/mayasyed/dbt-ecommerce-portfolio.git
cd dbt-ecommerce-portfolio
```

2. Configure your `~/.dbt/profiles.yml`:

```yaml
my_analytics_project:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: YOUR_GCP_PROJECT_ID
      dataset: dbt_analytics
      threads: 4
      timeout_seconds: 300
      location: US
```

3. Confirm the connection:

```bash
dbt debug
```

4. Run all models:

```bash
dbt run
```

5. Run all tests:

```bash
dbt test
```

6. Generate and serve documentation:

```bash
dbt docs generate
dbt docs serve
```

---

## Project Structure

```
my_analytics_project/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   ├── _sources.yml
│   │   ├── _staging.yml
│   │   ├── stg_order_items.sql
│   │   ├── stg_orders.sql
│   │   ├── stg_products.sql
│   │   └── stg_users.sql
│   └── marts/
│       ├── _marts.yml
│       ├── dim_orders.sql
│       ├── dim_products.sql
│       ├── dim_users.sql
│       └── fct_order_items.sql
└── README.md
```

---

## Dataset

Source: [thelook_ecommerce](https://console.cloud.google.com/marketplace/product/bigquery-public-data/thelook-ecommerce) — a Google-provided public BigQuery dataset simulating an e-commerce business with orders, customers, products, and inventory data.
