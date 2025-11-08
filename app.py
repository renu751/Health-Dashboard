import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fatty Liver & Diabetes Dashboard", layout="wide")
st.title("AI-Assisted Fatty Liver & Diabetes Dashboard (Beginner Version)")
st.caption("Educational use only — not medical advice.")

def fib4(age, ast, alt, platelets):
    if any(v is None for v in [age, ast, alt, platelets]) or alt <= 0 or platelets <= 0:
        return None
    return (age * ast) / (platelets * math.sqrt(alt))

def nfs(age, bmi, has_t2d, ast, alt, platelets, albumin):
    if any(v is None for v in [age, bmi, ast, alt, platelets, albumin]):
        return None
    return (-1.675 + 0.037*age + 0.094*bmi + 1.13*(1 if has_t2d else 0)
            + 0.99*(ast/alt) - 0.013*platelets - 0.66*albumin)

def homa_ir(glu_mg_dl, insulin_u_ml):
    if glu_mg_dl is None or insulin_u_ml is None: return None
    return (insulin_u_ml * glu_mg_dl) / 405.0

def eAG_from_a1c(a1c):
    if a1c is None: return None
    return 28.7 * a1c - 46.7

def categorize_fib4(x):
    if x is None: return "—"
    if x < 1.3: return "Low"
    if x <= 2.67: return "Indeterminate"
    return "High"

def categorize_nfs(x):
    if x is None: return "—"
    if x < -1.455: return "Low"
    if x <= 0.676: return "Indeterminate"
    return "High"

with st.sidebar:
    st.header("Enter latest values")
    age = st.number_input("Age (years)", 18, 100, 52)
    sex = st.selectbox("Sex", ["M","F"])
    weight = st.number_input("Weight (kg)", 30.0, 250.0, 86.0, 0.5)
    height = st.number_input("Height (cm)", 120.0, 220.0, 170.0, 0.5)
    ast = st.number_input("AST (U/L)", 1.0, 500.0, 40.0)
    alt = st.number_input("ALT (U/L)", 1.0, 500.0, 45.0)
    plate = st.number_input("Platelets (10^9/L)", 10.0, 800.0, 220.0)
    albumin = st.number_input("Albumin (g/dL)", 1.0, 6.5, 4.2)

    bmi = weight / ((height/100) ** 2)
    st.caption(f"Calculated BMI: **{bmi:.1f}**")

    has_t2d = st.checkbox("Type 2 Diabetes", True)
    fglu = st.number_input("Fasting Glucose (mg/dL)", 40.0, 400.0, 120.0)
    fins = st.number_input("Fasting Insulin (μU/mL)", 0.0, 200.0, 18.0)
    a1c = st.number_input("HbA1c (%)", 4.0, 14.0, 7.2, 0.1)

scores = {
    "FIB-4": fib4(age, ast, alt, plate),
    "NFS": nfs(age, bmi, has_t2d, ast, alt, plate, albumin),
    "HOMA-IR": homa_ir(fglu, fins),
    "eAG (mg/dL)": eAG_from_a1c(a1c)
}

c1,c2,c3,c4 = st.columns(4)
c1.metric("FIB-4", f"{scores['FIB-4']:.2f}" if scores['FIB-4'] else "—",
          help="Fibrosis screen: <1.3 low, 1.3–2.67 indeterminate, >2.67 high")
c2.metric("NAFLD Fibrosis Score", f"{scores['NFS']:.2f}" if scores['NFS'] else "—",
          help="< -1.455 low, -1.455 to 0.676 indeterminate, > 0.676 high")
c3.metric("HOMA-IR", f"{scores['HOMA-IR']:.2f}" if scores['HOMA-IR'] else "—",
          help="Higher = more insulin resistance")
c4.metric("eAG (mg/dL)", f"{scores['eAG (mg/dL)']:.0f}" if scores['eAG (mg/dL)'] else "—",
          help="Estimated average glucose from HbA1c")

st.subheader("Risk summary (simple rules)")
st.info(f"FIB-4: **{categorize_fib4(scores['FIB-4'])}**  |  NFS: **{categorize_nfs(scores['NFS'])}**")

st.subheader("Upload lab history CSV (optional)")
st.caption("Columns: timestamp, age_years, AST, ALT, platelets_10e9_L, albumin_g_dL, BMI, has_t2d, fasting_glucose_mg_dL, fasting_insulin_u_mL, HbA1c_pct")
labs_file = st.file_uploader("Choose labs CSV", type=["csv"], key="labs")

if labs_file:
    labs = pd.read_csv(labs_file, parse_dates=["timestamp"]).sort_values("timestamp")
    labs["FIB4"] = labs.apply(lambda r: fib4(r["age_years"], r["AST"], r["ALT"], r["platelets_10e9_L"]), axis=1)
    labs["NFS"] = labs.apply(lambda r: nfs(r["age_years"], r["BMI"], bool(r["has_t2d"]), r["AST"], r["ALT"], r["platelets_10e9_L"], r["albumin_g_dL"]), axis=1)
    labs["HOMA_IR"] = labs.apply(lambda r: homa_ir(r.get("fasting_glucose_mg_dL"), r.get("fasting_insulin_u_mL")), axis=1)
    labs["eAG_mg_dl"] = labs["HbA1c_pct"].apply(eAG_from_a1c)
    st.line_chart(labs.set_index("timestamp")[["FIB4","NFS"]])
    st.dataframe(labs[["timestamp","AST","ALT","platelets_10e9_L","albumin_g_dL","FIB4","NFS","HOMA_IR","eAG_mg_dl"]])

st.subheader("Upload CGM CSV (optional)")
st.caption("Columns: timestamp, glucose_mg_dl")
cgm_file = st.file_uploader("Choose CGM CSV", type=["csv"], key="cgm")

if cgm_file:
    cgm = pd.read_csv(cgm_file, parse_dates=["timestamp"]).sort_values("timestamp")
    cgm["in_range"] = cgm["glucose_mg_dl"].between(70,180).astype(int)
    tir = round(100*cgm["in_range"].mean(), 1)
    mean_glu = round(cgm["glucose_mg_dl"].mean(), 1)
    cv = round(100*cgm["glucose_mg_dl"].std()/cgm["glucose_mg_dl"].mean(), 1) if mean_glu else None
    st.line_chart(cgm.set_index("timestamp")["glucose_mg_dl"])
    st.caption(f"Time-in-Range (70–180): **{tir}%** | Mean: **{mean_glu} mg/dL** | CV: **{cv}%**")
    lows = (cgm["glucose_mg_dl"] < 70).sum()
    highs = (cgm["glucose_mg_dl"] > 250).sum()
    if lows >= 2: st.warning("Multiple low readings (<70 mg/dL). Consider medical guidance.")
    if highs >= 2: st.warning("Multiple very high readings (>250 mg/dL). Consider medical guidance.")
