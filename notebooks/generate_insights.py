"""
Generate the portfolio charts and headline figures from the dbt marts.

Run this AFTER `dbt run` has built the analytics marts. It reads the three
mart tables straight from BigQuery, saves three charts into ../images/, and
prints a HEADLINE FIGURES block that the README quotes.

Usage:
    pip install -r requirements.txt
    python generate_insights.py --project YOUR_GCP_PROJECT --dataset dbt_analytics
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import bigquery

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

# Consistent green and teal palette across all charts.
GREEN = "#16A34A"   # gross margin bars
TEAL  = "#0D9488"   # revenue bars and line charts
LABEL = "#FFFFFF"   # text on coloured bars
MUTED = "#6B7280"   # secondary annotation text

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.2,
    "axes.grid.axis": "x",
})


def load(client: bigquery.Client, dataset: str, table: str) -> pd.DataFrame:
    return client.query(f"select * from `{dataset}`.`{table}`").to_dataframe()


def chart_category_margin(df: pd.DataFrame) -> None:
    """
    Clustered horizontal bar chart: gross margin (green) and revenue (teal)
    side by side for the top 10 categories by gross margin value.
    Margin percentage is shown as a label inside the green bar so it
    never floats outside the chart area.
    """
    # Aggregate across departments (Men/Women) so each category appears once.
    # Recalculate gross_margin_pct from the combined totals.
    df_agg = (
        df.groupby("category", as_index=False)
        .agg(gross_revenue=("gross_revenue", "sum"), gross_margin=("gross_margin", "sum"))
    )
    df_agg["gross_margin_pct"] = df_agg["gross_margin"] / df_agg["gross_revenue"]

    top = (
        df_agg.sort_values("gross_margin", ascending=False)
        .head(10)
        .iloc[::-1]
        .reset_index(drop=True)
    )

    bar_h = 0.38
    y = np.arange(len(top))

    fig, ax = plt.subplots(figsize=(9, 6))

    # Revenue bars (teal, upper slot)
    ax.barh(
        y + bar_h / 2,
        top["gross_revenue"],
        height=bar_h,
        color=TEAL,
        label="Gross revenue (£)",
    )

    # Gross margin bars (green, lower slot)
    gm_bars = ax.barh(
        y - bar_h / 2,
        top["gross_margin"],
        height=bar_h,
        color=GREEN,
        label="Gross margin (£)",
    )

    # Margin percentage label placed at the midpoint of each green bar.
    # This avoids the floating label issue caused by positioning at bar end.
    for bar, pct in zip(gm_bars, top["gross_margin_pct"]):
        w  = bar.get_width()
        cx = w * 0.5
        cy = bar.get_y() + bar.get_height() / 2
        ax.text(
            cx, cy, f"{pct:.0%}",
            ha="center", va="center",
            fontsize=8, color=LABEL, fontweight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(top["category"], fontsize=10)
    ax.set_xlabel("Value (£)")
    ax.set_title("Top 10 Categories by Gross Margin (£)", pad=14, fontsize=12)
    ax.legend(loc="lower right", framealpha=0.9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:,.0f}"))

    fig.tight_layout()
    fig.savefig(IMAGES_DIR / "category_margin.png")
    plt.close(fig)


def chart_retention(df: pd.DataFrame) -> None:
    df = df.sort_values("cohort_month")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(
        df["cohort_month"], df["repeat_purchase_rate"],
        color=TEAL, marker="o", ms=4, linewidth=2,
    )
    ax.fill_between(df["cohort_month"], df["repeat_purchase_rate"],
                    alpha=0.1, color=TEAL)
    ax.set_title("Repeat Purchase Rate by Acquisition Cohort", pad=14, fontsize=12)
    ax.set_ylabel("Share of customers who ordered again")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(IMAGES_DIR / "retention_cohorts.png")
    plt.close(fig)


def chart_channel(df: pd.DataFrame) -> None:
    df = df.sort_values("revenue_per_customer", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(df["traffic_source"], df["revenue_per_customer"], color=GREEN)
    ax.set_title("Revenue per Customer by Acquisition Channel (£)", pad=14, fontsize=12)
    ax.set_xlabel("Revenue per customer (£)")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:,.0f}"))

    # Repeat purchase rate label inside each bar
    for bar, rep in zip(bars, df["repeat_purchase_rate"]):
        w  = bar.get_width()
        cx = w * 0.5
        cy = bar.get_y() + bar.get_height() / 2
        ax.text(
            cx, cy, f"{rep:.0%} repeat",
            ha="center", va="center",
            fontsize=8, color=LABEL, fontweight="bold",
        )

    fig.tight_layout()
    fig.savefig(IMAGES_DIR / "channel_value.png")
    plt.close(fig)


def headline_figures(
    cat: pd.DataFrame, ret: pd.DataFrame, chan: pd.DataFrame
) -> None:
    overall_repeat = ret["repeat_customers"].sum() / ret["new_customers"].sum()
    best_margin    = cat.sort_values("gross_margin_pct", ascending=False).iloc[0]
    worst_margin   = cat.sort_values("gross_margin_pct").iloc[0]
    worst_returns  = cat.sort_values("return_rate", ascending=False).iloc[0]
    best_channel   = chan.sort_values("revenue_per_customer", ascending=False).iloc[0]

    print("\n" + "=" * 60)
    print("HEADLINE FIGURES  (paste these into the README)")
    print("=" * 60)
    print(f"Overall repeat purchase rate : {overall_repeat:.1%}")
    print(f"Highest margin category      : {best_margin['category']} "
          f"({best_margin['gross_margin_pct']:.0%} margin)")
    print(f"Lowest margin category       : {worst_margin['category']} "
          f"({worst_margin['gross_margin_pct']:.0%} margin)")
    print(f"Highest return rate          : {worst_returns['category']} "
          f"({worst_returns['return_rate']:.0%} of items returned)")
    print(f"Best channel by rev/customer : {best_channel['traffic_source']} "
          f"(£{best_channel['revenue_per_customer']:.0f}, "
          f"{best_channel['repeat_purchase_rate']:.0%} repeat)")
    print("=" * 60 + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="GCP project id")
    p.add_argument("--dataset", default="dbt_analytics", help="dbt target dataset")
    args = p.parse_args()

    client = bigquery.Client(project=args.project)
    cat  = load(client, args.dataset, "mart_category_performance")
    ret  = load(client, args.dataset, "mart_customer_retention")
    chan = load(client, args.dataset, "mart_channel_performance")

    chart_category_margin(cat)
    chart_retention(ret)
    chart_channel(chan)
    headline_figures(cat, ret, chan)
    print(f"Charts saved to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
