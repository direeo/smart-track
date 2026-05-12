"""
synthetic_data_generator.py
============================
SmartTrack KPI — Synthetic Dataset Generator

This script generates a synthetic dataset of 500 KPI completion records
for training and evaluating the Random Forest classification model.

Each record represents one employee working toward one assigned KPI.
The outcome column (met_target) indicates whether the employee completed
at least 100% of their assigned goal by the deadline.

Author : Ojo Esther Temidire (22CG031908)
Project: Implementation of an Intelligent KPI Tracking System
         with Predictive Analytics for Workforce Management
Supervisor: Prof. Aderonke A. Oni
Institution: Covenant University, Ota
"""

import numpy as np
import pandas as pd
import random

# ── Reproducibility ────────────────────────────────────────────────────────
np.random.seed(42)
random.seed(42)

# ── Configuration ──────────────────────────────────────────────────────────
N_RECORDS   = 500
OUTPUT_FILE = "synthetic_kpi_data.csv"

# ── KPI Templates ──────────────────────────────────────────────────────────
# These represent realistic workplace KPI types and target ranges.
# Target values are chosen to reflect what is achievable in 60–150 days.
KPI_TEMPLATES = [
    {"title": "Close support tickets",    "unit": "tickets",  "min": 50,  "max": 200},
    {"title": "Deliver product features", "unit": "features", "min": 10,  "max": 50},
    {"title": "Complete code reviews",    "unit": "reviews",  "min": 40,  "max": 150},
    {"title": "Conduct client calls",     "unit": "calls",    "min": 30,  "max": 120},
    {"title": "Resolve bug reports",      "unit": "bugs",     "min": 20,  "max": 80},
    {"title": "Write documentation",      "unit": "pages",    "min": 15,  "max": 60},
    {"title": "Deploy system updates",    "unit": "updates",  "min": 8,   "max": 40},
    {"title": "Onboard new clients",      "unit": "clients",  "min": 5,   "max": 25},
]

# ── Work Behaviour Profiles ────────────────────────────────────────────────
# Each profile represents a distinct pattern of how an employee progresses
# through a KPI cycle. The success_prob value is the baseline probability
# that an employee with this profile meets their target.
#
# Profile descriptions:
#   steady        — consistent output throughout; low risk of missing
#   slow_starter  — begins slowly, accelerates in the second half
#   strong_starter— begins fast, gradually slows down
#   struggling    — low output throughout, infrequent updates; high risk
#
PROFILES = {
    "steady":         {"weight": 0.30, "success_prob": 0.80},
    "slow_starter":   {"weight": 0.20, "success_prob": 0.50},
    "strong_starter": {"weight": 0.25, "success_prob": 0.65},
    "struggling":     {"weight": 0.25, "success_prob": 0.20},
}

# ── Feature Definitions ────────────────────────────────────────────────────
# These seven features are the inputs to the Random Forest model.
# All features can be computed from data that accumulates naturally
# in the SmartTrack KPI system as employees submit progress updates.
#
#   pace_ratio          — actual daily output rate / required daily rate
#                         >1 means ahead of schedule; <1 means behind
#
#   halfway_completion  — fraction of target completed by the midpoint date
#                         strong early indicator of final outcome
#
#   update_frequency    — average number of progress updates per week
#                         reflects engagement with the tracking system
#
#   pace_trend          — difference between second-half and first-half
#                         average output rates; positive = accelerating
#
#   days_remaining_pct  — days remaining at last update as fraction of
#                         total KPI duration; lower = completed earlier
#
#   fell_behind         — binary flag: 1 if the employee's cumulative
#                         progress fell more than 30% below the expected
#                         pace at any recorded point
#
#   n_updates           — total number of progress updates submitted
# ──────────────────────────────────────────────────────────────────────────


def generate_record(employee_id: int) -> dict:
    """
    Generate one synthetic KPI completion record.

    The generation process:
    1. Randomly assign a KPI template and duration.
    2. Randomly assign a work behaviour profile.
    3. Determine the outcome (met or missed) based on the profile's
       success probability, with some random variation.
    4. Generate feature values using normal distributions centred
       around values that are statistically consistent with the
       determined outcome, while maintaining enough overlap between
       the two classes to produce realistic model difficulty.
    5. Assign a profile consistent with the outcome.
    """

    # ── Step 1: KPI configuration ──────────────────────────────────────
    template     = random.choice(KPI_TEMPLATES)
    target       = random.randint(template["min"], template["max"])
    duration     = random.randint(60, 150)          # KPI duration in days

    # ── Step 2: Work profile ───────────────────────────────────────────
    profile_name = random.choices(
        list(PROFILES.keys()),
        weights=[p["weight"] for p in PROFILES.values()]
    )[0]
    profile = PROFILES[profile_name]

    # ── Step 3: Outcome determination ─────────────────────────────────
    # The outcome is determined first. Feature values are then generated
    # to be consistent with that outcome. This approach avoids perfectly
    # separated classes while maintaining meaningful statistical differences
    # between the two groups.
    met_target = 1 if random.random() < profile["success_prob"] else 0

    # ── Step 4: Feature generation ─────────────────────────────────────
    # Normal distributions are used so that feature values vary realistically
    # within each class. The mean and standard deviation for each feature
    # differ between the two classes to create learnable patterns, but the
    # standard deviations are set wide enough to produce overlap.

    if met_target == 1:
        pace_ratio         = float(np.clip(np.random.normal(1.08, 0.28), 0.50, 2.0))
        halfway_completion = float(np.clip(np.random.normal(0.52, 0.15), 0.15, 0.90))
        update_frequency   = float(np.clip(np.random.normal(1.05, 0.35), 0.20, 2.50))
        pace_trend         = float(np.random.normal(0.30, 1.20))
        days_remaining_pct = float(np.clip(np.random.normal(0.12, 0.10), 0.00, 0.50))
        fell_behind        = 1 if random.random() < 0.20 else 0
        n_updates          = max(3, int(np.random.normal(12, 4)))
    else:
        pace_ratio         = float(np.clip(np.random.normal(0.72, 0.28), 0.10, 1.40))
        halfway_completion = float(np.clip(np.random.normal(0.32, 0.15), 0.02, 0.70))
        update_frequency   = float(np.clip(np.random.normal(0.65, 0.30), 0.10, 1.80))
        pace_trend         = float(np.random.normal(-0.30, 1.20))
        days_remaining_pct = float(np.clip(np.random.normal(0.28, 0.14), 0.00, 0.70))
        fell_behind        = 1 if random.random() < 0.65 else 0
        n_updates          = max(2, int(np.random.normal(7, 3)))

    # ── Step 5: Profile assignment consistent with outcome ──────────────
    if met_target == 1:
        work_style = random.choices(
            ["steady", "strong_starter", "slow_starter", "struggling"],
            weights=[0.45, 0.28, 0.22, 0.05]
        )[0]
    else:
        work_style = random.choices(
            ["steady", "strong_starter", "slow_starter", "struggling"],
            weights=[0.15, 0.20, 0.25, 0.40]
        )[0]

    return {
        "employee_id":        employee_id,
        "kpi_title":          template["title"],
        "unit":               template["unit"],
        "target":             target,
        "duration_days":      duration,
        "work_style":         work_style,
        "pace_ratio":         round(pace_ratio, 4),
        "halfway_completion": round(halfway_completion, 4),
        "update_frequency":   round(update_frequency, 4),
        "pace_trend":         round(pace_trend, 4),
        "days_remaining_pct": round(days_remaining_pct, 4),
        "fell_behind":        fell_behind,
        "n_updates":          n_updates,
        "met_target":         met_target,
    }


# ── Main execution ─────────────────────────────────────────────────────────
if __name__ == "__main__":

    print(f"Generating {N_RECORDS} synthetic KPI completion records...")
    records = [generate_record(i) for i in range(1, N_RECORDS + 1)]

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_FILE, index=False)

    # ── Summary statistics ─────────────────────────────────────────────
    print(f"\nDataset saved to: {OUTPUT_FILE}")
    print(f"\n{'='*50}")
    print("CLASS DISTRIBUTION")
    print(f"{'='*50}")
    print(f"  Met target:    {df['met_target'].sum()} "
          f"({df['met_target'].mean()*100:.1f}%)")
    print(f"  Missed target: {(df['met_target']==0).sum()} "
          f"({(df['met_target']==0).mean()*100:.1f}%)")

    print(f"\n{'='*50}")
    print("FEATURE MEANS BY OUTCOME")
    print(f"{'='*50}")
    summary = df.groupby("met_target")[
        ["pace_ratio", "halfway_completion", "update_frequency",
         "fell_behind", "n_updates"]
    ].mean().round(3)
    summary.index = ["Missed (0)", "Met (1)"]
    print(summary.to_string())

    print(f"\n{'='*50}")
    print("WORK STYLE DISTRIBUTION")
    print(f"{'='*50}")
    print(df["work_style"].value_counts().to_string())
    print(f"\nGeneration complete.")