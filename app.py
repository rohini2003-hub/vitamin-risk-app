"""
Streamlit Vitamin D & B12 Deficiency Risk Screening Tool
UAE-focused survey interface with SHAP explainability.

Run with:  streamlit run app.py
"""

import joblib
import numpy as np
import pandas as pd
import shap
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from feature_mapping import UAE_SURVEY

# ── Constants ────────────────────────────────────────────────────────────────
MODEL_DIR = "models"

RISK_COLORS = {
    "Low":    "#2ecc71",   # green
    "Medium": "#f39c12",   # amber
    "High":   "#e74c3c",   # red
}
RISK_EMOJI = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
RISK_ADVICE = {
    "Low": (
        "Your lifestyle indicators suggest a **low risk** of deficiency. "
        "Keep maintaining a balanced diet and regular outdoor activity."
    ),
    "Medium": (
        "Your indicators suggest a **borderline / insufficient** level. "
        "Consider increasing dietary sources and discussing supplementation "
        "with your doctor. A blood test would give you certainty."
    ),
    "High": (
        "Your indicators suggest a **high risk of deficiency**. "
        "We strongly recommend consulting a healthcare professional and "
        "requesting a blood test. Do not self-prescribe high-dose supplements."
    ),
}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vitamin D & B12 Risk Screening — UAE",
    page_icon="🩺",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { max-width: 780px; }
    .risk-box {
        border-radius: 12px;
        padding: 18px 24px;
        margin: 12px 0 20px 0;
        font-size: 1.1rem;
        font-weight: 500;
    }
    .risk-low    { background: #d5f5e3; color: #1a5c35; border-left: 6px solid #2ecc71; }
    .risk-medium { background: #fef9e7; color: #7d5a00; border-left: 6px solid #f39c12; }
    .risk-high   { background: #fadbd8; color: #7b241c; border-left: 6px solid #e74c3c; }
    .section-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #4a4a6a;
        margin-top: 28px;
        margin-bottom: 4px;
        border-bottom: 1px solid #e0e0e0;
        padding-bottom: 4px;
    }
    .disclaimer {
        background: #f0f4ff;
        border-left: 4px solid #5b8dee;
        border-radius: 6px;
        padding: 10px 16px;
        font-size: 0.88rem;
        color: #3a3a5c;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ── Model loading ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading models…")
def load_artifacts(nutrient_key):
    model      = joblib.load(f"{MODEL_DIR}/{nutrient_key}_best_model.joblib")
    feat_cols  = joblib.load(f"{MODEL_DIR}/{nutrient_key}_feature_cols.joblib")
    background = joblib.load(f"{MODEL_DIR}/{nutrient_key}_shap_background.joblib")
    return model, feat_cols, background


# ── Survey form ──────────────────────────────────────────────────────────────
def render_survey():
    """Render UAE survey questions and return a dict {feature: numeric_value}."""
    answers = {}

    sections = {
        "👤 About You":              ["age", "sex", "ethnicity", "education", "income_to_poverty_ratio"],
        "☀️ Sun Exposure & Activity": ["exam_season", "sedentary_minutes_per_day", "vigorous_activity"],
        "🥗 Diet":                   ["dietary_vitamin_d_mcg", "dietary_vitamin_b12_mcg"],
        "💊 Supplements":            ["takes_any_supplement", "supplement_vitamin_d_mcg", "supplement_vitamin_b12_mcg"],
    }

    # build a lookup from feature name → question definition
    q_by_feature = {q["feature"]: q for q in UAE_SURVEY}

    for section_title, features in sections.items():
        st.markdown(f'<div class="section-header">{section_title}</div>', unsafe_allow_html=True)
        for feat in features:
            q = q_by_feature[feat]
            help_text = q.get("help", None)

            if q["type"] == "select":
                display_labels = [opt[0] for opt in q["options"]]
                default_idx = next(
                    (i for i, (lbl, _) in enumerate(q["options"]) if lbl == q["default"]),
                    0,
                )
                chosen_label = st.selectbox(
                    q["label"], display_labels,
                    index=default_idx,
                    help=help_text,
                    key=f"q_{feat}",
                )
                # look up the numeric value for the chosen label
                value = next(v for lbl, v in q["options"] if lbl == chosen_label)

            elif q["type"] == "slider":
                value = st.slider(
                    q["label"],
                    min_value=q["min"],
                    max_value=q["max"],
                    step=q["step"],
                    value=q["default"],
                    help=help_text,
                    key=f"q_{feat}",
                )

            elif q["type"] == "number":
                value = st.number_input(
                    q["label"],
                    min_value=q.get("min", 0.0),
                    max_value=q.get("max", 9999.0),
                    step=q.get("step", 1.0),
                    value=float(q["default"]),
                    help=help_text,
                    key=f"q_{feat}",
                )

            answers[feat] = value

    return answers


# ── SHAP explanation chart ───────────────────────────────────────────────────
def shap_chart(model, background, input_df, feat_cols, pred_class, nutrient_label):
    """Return a matplotlib figure with the top-5 SHAP drivers for pred_class."""
    explainer   = shap.Explainer(model.predict_proba, background)
    shap_values = explainer(input_df)

    classes   = model.named_steps["model"].classes_
    pred_idx  = list(classes).index(pred_class)
    vals      = shap_values.values[0, :, pred_idx]
    feat_names = shap_values.feature_names

    # human-readable feature labels
    pretty = {
        "age":                       "Age",
        "sex":                       "Sex",
        "ethnicity":                 "Ethnicity",
        "income_to_poverty_ratio":   "Income level",
        "education":                 "Education level",
        "dietary_vitamin_d_mcg":     "Dietary Vitamin D intake",
        "dietary_vitamin_b12_mcg":   "Dietary Vitamin B12 intake",
        "takes_any_supplement":      "Takes supplements",
        "supplement_vitamin_d_mcg":  "Vitamin D supplement dose",
        "supplement_vitamin_b12_mcg":"Vitamin B12 supplement dose",
        "sedentary_minutes_per_day": "Sedentary time per day",
        "vigorous_activity":         "Vigorous physical activity",
        "exam_season":               "Season / sun exposure",
    }
    labels = [pretty.get(f, f) for f in feat_names]

    order = np.argsort(-np.abs(vals))[:5]
    top_vals   = [vals[i]   for i in order][::-1]
    top_labels = [labels[i] for i in order][::-1]

    colors = ["#e74c3c" if v > 0 else "#3498db" for v in top_vals]

    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = ax.barh(top_labels, top_vals, color=colors, edgecolor="none", height=0.55)
    ax.axvline(0, color="#555", linewidth=0.8, linestyle="--")
    ax.set_xlabel("SHAP value  (→ increases risk  |  ← decreases risk)", fontsize=9)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title(f"Why this {nutrient_label} risk prediction?", fontsize=10, fontweight="bold")

    red_patch  = mpatches.Patch(color="#e74c3c", label="Pushes risk higher")
    blue_patch = mpatches.Patch(color="#3498db", label="Pushes risk lower")
    ax.legend(handles=[red_patch, blue_patch], fontsize=8, loc="lower right")

    fig.tight_layout()
    return fig


# ── Single nutrient result card ──────────────────────────────────────────────
def render_result(nutrient_key, nutrient_label, input_df):
    model, feat_cols, background = load_artifacts(nutrient_key)
    row  = input_df[feat_cols]
    pred = model.predict(row)[0]
    proba = model.predict_proba(row)[0]
    classes = model.named_steps["model"].classes_

    # ── Risk label ────────────────────────────────────────────
    css_class = {"Low": "risk-low", "Medium": "risk-medium", "High": "risk-high"}[pred]
    emoji     = RISK_EMOJI[pred]
    st.markdown(
        f'<div class="risk-box {css_class}">'
        f'{emoji} <strong>{nutrient_label} deficiency risk: {pred}</strong><br>'
        f'<span style="font-weight:400;font-size:0.95rem">{RISK_ADVICE[pred]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Probability bar chart ─────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**Model confidence across risk levels**")
        prob_df = pd.DataFrame({
            "Risk level":  list(classes),
            "Probability": list(proba),
        }).set_index("Risk level")
        st.bar_chart(prob_df, color="#5b8dee", height=200)

    # ── SHAP chart ────────────────────────────────────────────
    with col2:
        st.markdown("**Top factors driving this prediction**")
        with st.spinner("Calculating explanations…"):
            fig = shap_chart(model, background, row, feat_cols, pred, nutrient_label)
        st.pyplot(fig)
        plt.close(fig)


# ── Main app ─────────────────────────────────────────────────────────────────
def main():
    # Header
    st.title("🩺 Vitamin D & B12 Deficiency Risk Screening")


    # How it works expander
    with st.expander("ℹ️ How does this tool work?"):
        st.markdown("""
**Training data:** Real lab-confirmed Vitamin D and B12 blood results from ~5,400 US adults
(NHANES 2013–2014), labelled using clinical cut-offs (Holick, 2007 for Vitamin D).

**Models trained:** Logistic Regression, Decision Tree, and Random Forest — the best-performing
model (Random Forest) is used here.

**For UAE residents:** Since a blood test isn't required, you answer lifestyle and dietary questions.
The model applies the patterns it learned from confirmed deficiency cases to estimate your risk.

**Explainability:** SHAP (SHapley Additive exPlanations) shows exactly which of your answers pushed
the prediction toward higher or lower risk — making the model transparent, not a black box.

**Limitation:** The model was trained on US data; UAE-specific factors (e.g. cultural diet,
extreme heat reducing outdoor time) are approximated. Treat results as an awareness indicator.
        """)

    st.markdown("---")
    st.subheader("📋 Answer the questions below")
    st.caption("All questions are anonymous. Your answers are not stored or transmitted.")

    # Survey form
    answers = render_survey()

    st.markdown("---")

    # Submit button
    if st.button("🔍 Get my risk screening result", type="primary", use_container_width=True):
        # Build input DataFrame in the exact column order the models expect
        _, feat_cols, _ = load_artifacts("vitamin_d")
        input_df = pd.DataFrame([answers])[feat_cols]

        st.markdown("## 📊 Your Results")
        st.caption("Results are based on the lifestyle and dietary information you provided.")

        # Vitamin D
        with st.container():
            st.markdown("### ☀️ Vitamin D")
            render_result("vitamin_d", "Vitamin D", input_df)

        st.divider()

        # Vitamin B12
        with st.container():
            st.markdown("### 🥩 Vitamin B12")
            render_result("vitamin_b12", "Vitamin B12", input_df)

        st.divider()

        # Recommendations footer
        st.markdown("### 💡 General Recommendations")
        st.markdown("""
| Factor | What you can do |
|---|---|
| **Sun exposure** | 10–20 minutes of midday sun on arms/legs, 3–4× per week (avoid UAE summer peak hours) |
| **Vitamin D foods** | Fatty fish (salmon, sardines), egg yolks, fortified dairy/cereals |
| **Vitamin B12 foods** | Meat, poultry, fish, eggs, dairy — if vegetarian/vegan, supplementation is usually necessary |
| **Supplements** | Only take high-dose supplements under medical supervision |
| **Blood test** | The definitive check — ask your GP for serum 25(OH)D and serum B12 levels |
        """)




if __name__ == "__main__":
    main()
