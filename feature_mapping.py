"""
Central place that defines:
  1. Which raw NHANES variables feed each model feature (NHANES_FEATURES)
  2. Clinical cut-offs used to derive the Low/Medium/High labels (CUTOFFS)
  3. How a UAE survey answer maps onto that same model feature (SURVEY_TO_MODEL_FEATURE)
"""

# ---------------------------------------------------------------------------
# 1. NHANES variables that become model features
# ---------------------------------------------------------------------------
NHANES_FEATURES = {
    # demographics
    "age":                      "RIDAGEYR",   # DEMO_H
    "sex":                      "RIAGENDR",   # DEMO_H  (1=Male, 2=Female)
    "ethnicity":                "RIDRETH3",   # DEMO_H
    "education":                "DMDEDUC2",   # DEMO_H

    # dietary intake (24-hr recall, food only)
    "dietary_vitamin_d_mcg":    "DR1TVD",     # DR1TOT_H
    "dietary_vitamin_b12_mcg":  "DR1TVB12",   # DR1TOT_H

    # supplement use
    "takes_any_supplement":     "DSDCOUNT",   # DSQTOT_H
    "supplement_vitamin_d_mcg": "DSQTVD",     # DSQTOT_H
    "supplement_vitamin_b12_mcg":"DSQTVB12",  # DSQTOT_H

    # lifestyle / activity proxies
    "sedentary_minutes_per_day":"PAD680",     # PAQ_H
    "vigorous_activity":        "PAQ650",     # PAQ_H
    "exam_season":              "RIDEXMON",   # DEMO_H  (1=Nov-Apr, 2=May-Oct)

    # smoking
    "smoking_status":           "SMQ040",     # SMQ_H
}

# ---------------------------------------------------------------------------
# 2. Clinical cut-offs for label derivation
# ---------------------------------------------------------------------------
# Vitamin D: Holick (2007)
VITAMIN_D_CUTOFFS_NMOL_L = {
    "high_risk_below":   30,   # < 30 nmol/L  = deficient  → High risk
    "medium_risk_below": 50,   # 30-<50 nmol/L = insufficient → Medium risk
                               # >= 50 nmol/L  = sufficient  → Low risk
}

# Vitamin B12: widely-used clinical thresholds
VITAMIN_B12_CUTOFFS_PG_ML = {
    "high_risk_below":   200,  # < 200 pg/mL  = deficient   → High risk
    "medium_risk_below": 300,  # 200-<300 pg/mL = borderline → Medium risk
                               # >= 300 pg/mL  = normal     → Low risk
}

# ---------------------------------------------------------------------------
# 3. UAE survey questions → model features
#
# Each entry:
#   "feature_name"  : the key that matches NHANES_FEATURES above
#   "label"         : the question shown in the Streamlit app
#   "type"          : "select" | "slider" | "number"
#   "options"       : list of (display_text, numeric_value) for "select"
#   "min/max/step"  : for "slider" / "number"
#   "default"       : default widget value
#   "help"          : optional tooltip
# ---------------------------------------------------------------------------
UAE_SURVEY = [

    # ── Demographics ────────────────────────────────────────────────────────
    {
        "feature": "age",
        "label":   "What is your age?",
        "type":    "slider",
        "min": 18, "max": 80, "step": 1, "default": 30,
        "help":    "Your current age in years.",
    },
    {
        "feature": "sex",
        "label":   "What is your biological sex?",
        "type":    "select",
        "options": [("Male", 1), ("Female", 2)],
        "default": "Male",
        "help":    "As recorded for health screening purposes.",
    },
    {
        "feature": "ethnicity",
        "label":   "Which best describes your ethnic background?",
        "type":    "select",
        # RIDRETH3: 1=Mexican American, 2=Other Hispanic, 3=Non-Hispanic White,
        #           4=Non-Hispanic Black, 6=Non-Hispanic Asian, 7=Other/Multi
        # For UAE we map the most relevant groups available in NHANES
        "options": [
            ("Arab / Middle Eastern",       7),   # maps to Other/Multi-racial
            ("South Asian (Indian/Pakistani/Bangladeshi)", 6),  # Asian proxy
            ("East / Southeast Asian",      6),
            ("White / European",            3),
            ("Black / African",             4),
            ("Other / Prefer not to say",   7),
        ],
        "default": "Arab / Middle Eastern",
        "help":    "Used as a statistical proxy — the model was trained on US data so "
                   "Middle Eastern is mapped to the closest available NHANES category.",
    },
    {
        "feature": "education",
        "label":   "What is your highest level of education?",
        "type":    "select",
        # DMDEDUC2: 1=<9th grade, 2=9-11th, 3=High school/GED,
        #           4=Some college, 5=College graduate+
        "options": [
            ("Less than secondary school",          1),
            ("Secondary school (high school)",      3),
            ("Some university / diploma",           4),
            ("Bachelor's degree",                   5),
            ("Postgraduate degree (Master's/PhD)",  5),
        ],
        "default": "Bachelor's degree",
    },

    # ── Sun Exposure / Season proxy ──────────────────────────────────────────
    {
        "feature": "exam_season",
        "label":   "During which season do you spend the most time outdoors?",
        "type":    "select",
        # RIDEXMON: 1 = November–April (low sun), 2 = May–October (high sun)
        # In UAE context: summer (Jun-Sep) = indoors due to heat → low sun exposure
        #                 winter (Oct-May) = outdoors more → higher sun exposure
        "options": [
            ("Winter / cooler months (Oct–May) — more time outdoors", 2),
            ("Summer (Jun–Sep) — mostly indoors due to heat",          1),
        ],
        "default": "Winter / cooler months (Oct–May) — more time outdoors",
        "help":    "In the UAE, most people avoid outdoor activity in summer due to extreme heat, "
                   "reducing sun exposure and Vitamin D synthesis.",
    },

    # ── Physical Activity ────────────────────────────────────────────────────
    {
        "feature": "sedentary_minutes_per_day",
        "label":   "On a typical day, how many hours do you spend sitting or sedentary "
                   "(e.g. desk work, watching TV, driving)?",
        "type":    "select",
        # PAD680 is in minutes
        "options": [
            ("Less than 4 hours",    180),
            ("4–6 hours",            300),
            ("6–8 hours",            420),
            ("8–10 hours",           540),
            ("More than 10 hours",   660),
        ],
        "default": "6–8 hours",
        "help":    "More sedentary time is associated with less outdoor activity and lower Vitamin D.",
    },
    {
        "feature": "vigorous_activity",
        "label":   "Do you do vigorous physical activity (e.g. running, gym, sport) "
                   "for at least 10 minutes at a time?",
        "type":    "select",
        # PAQ650: 1=Yes, 2=No
        "options": [
            ("Yes", 1),
            ("No",  2),
        ],
        "default": "No",
        "help":    "Vigorous activity is a proxy for outdoor exposure and general health behaviour.",
    },

    # ── Diet ─────────────────────────────────────────────────────────────────
    {
        "feature": "dietary_vitamin_d_mcg",
        "label":   "How often do you eat fatty/oily fish (salmon, sardines, mackerel, tuna)?",
        "type":    "select",
        # DR1TVD is total dietary Vit D in mcg; we estimate from frequency
        # Average serving of fatty fish ≈ 10–15 mcg Vit D
        "options": [
            ("Never or rarely",              0.0),
            ("Once or twice a month",        1.5),
            ("Once a week",                  3.5),
            ("2–3 times a week",             8.0),
            ("4 or more times a week",      14.0),
        ],
        "default": "Once a week",
        "help":    "Fatty fish is the richest natural food source of Vitamin D.",
    },
    {
        "feature": "dietary_vitamin_b12_mcg",
        "label":   "How would you describe your overall intake of animal products "
                   "(meat, fish, eggs, dairy)?",
        "type":    "select",
        # DR1TVB12 is total dietary B12 in mcg
        # Typical daily intake: vegan≈0, vegetarian≈1-2, omnivore≈4-6 mcg
        "options": [
            ("Vegan — no animal products",              0.2),
            ("Vegetarian — dairy/eggs only",            1.5),
            ("Occasional meat/fish (1–2×/week)",        2.5),
            ("Regular meat/fish (most days)",           5.0),
            ("High — meat or fish at almost every meal",7.0),
        ],
        "default": "Regular meat/fish (most days)",
        "help":    "Vitamin B12 is found almost exclusively in animal-sourced foods.",
    },

    # ── Supplements ──────────────────────────────────────────────────────────
    {
        "feature": "takes_any_supplement",
        "label":   "Do you currently take any dietary supplements or vitamins?",
        "type":    "select",
        # DSDCOUNT = number of supplements taken; 0 = none
        "options": [
            ("No supplements",                    0),
            ("Yes — 1 supplement",                1),
            ("Yes — 2 or more supplements",       3),
        ],
        "default": "No supplements",
    },
    {
        "feature": "supplement_vitamin_d_mcg",
        "label":   "If you take a Vitamin D supplement, what is the daily dose?",
        "type":    "select",
        # DSQTVD in mcg (IU ÷ 40 = mcg)
        "options": [
            ("I don't take Vitamin D supplements",     0.0),
            ("Low dose (400–800 IU / 10–20 mcg)",     15.0),
            ("Standard dose (1000 IU / 25 mcg)",      25.0),
            ("High dose (2000 IU / 50 mcg)",          50.0),
            ("Very high dose (4000+ IU / 100+ mcg)", 100.0),
        ],
        "default": "I don't take Vitamin D supplements",
        "help":    "1 IU of Vitamin D = 0.025 mcg.",
    },
    {
        "feature": "supplement_vitamin_b12_mcg",
        "label":   "If you take a Vitamin B12 supplement, what is the daily dose?",
        "type":    "select",
        # DSQTVB12 in mcg
        "options": [
            ("I don't take Vitamin B12 supplements",  0.0),
            ("Low dose (up to 10 mcg)",               5.0),
            ("Standard dose (25–100 mcg)",           50.0),
            ("High dose (250–500 mcg)",             250.0),
            ("Very high dose (1000+ mcg)",         1000.0),
        ],
        "default": "I don't take Vitamin B12 supplements",
    },

    # ── Smoking ───────────────────────────────────────────────────────────────
    {
        "feature": "smoking_status",
        "label":   "Do you currently smoke cigarettes or use tobacco products?",
        "type":    "select",
        # SMQ040: 1=Every day, 2=Some days, 3=Not at all
        "options": [
            ("No — I do not smoke",           3),
            ("Occasionally (some days)",      2),
            ("Yes — I smoke every day",       1),
        ],
        "default": "No — I do not smoke",
    },
]
