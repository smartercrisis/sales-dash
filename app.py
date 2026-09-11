import streamlit as st
import pandas as pd
import plotly.express as px

from core import CITY_COORDS, normalize_city, clean_data

st.set_page_config(page_title="Sales & Returns Dashboard", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .high-loss-badge {
        display:inline-block; background:#ff3b3b22; color:#ff5c5c; border:1px solid #ff3b3b55;
        padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.75rem; margin-right:8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Sales & Returns Dashboard")
st.caption("Upload a sales export, map your columns, and get a clean analytics view.")

uploaded = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if not uploaded:
    st.info("Upload a CSV or Excel file to get started.")
    st.stop()

raw_df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)

st.subheader("1. Map Your Columns")
st.caption("Tell the app which of your columns is which — every export is laid out differently.")
cols = list(raw_df.columns)
none_opt = "-- none --"

c1, c2 = st.columns(2)
with c1:
    date_col = st.selectbox("Order date column", [none_opt] + cols)
    city_col = st.selectbox("City column", [none_opt] + cols)
    product_col = st.selectbox("Product column", [none_opt] + cols)
with c2:
    amount_col = st.selectbox("Order amount column", [none_opt] + cols)
    returned_col = st.selectbox("Returned flag column (optional)", [none_opt] + cols)

col_map = {
    "date": None if date_col == none_opt else date_col,
    "city": None if city_col == none_opt else city_col,
    "product": None if product_col == none_opt else product_col,
    "amount": None if amount_col == none_opt else amount_col,
    "returned": None if returned_col == none_opt else returned_col,
}

if not (col_map["date"] and col_map["amount"] and col_map["product"]):
    st.info("Map at least Date, Product, and Amount columns to continue.")
    st.stop()

try:
    df, report = clean_data(raw_df.copy(), col_map)
except ValueError as e:
    st.error(str(e))
    st.stop()

st.subheader("2. Cleaning Report")
r1, r2, r3, r4 = st.columns(4)
r1.metric("Rows Uploaded", report["total_rows"])
r2.metric("Rows Dropped (invalid)", report["dropped_rows"])
r3.metric("Rows Cleaned", report["clean_rows"])
r4.metric("Unmapped Cities", report["unmapped_cities"])

if report["unmapped_cities"] > 0:
    st.warning(
        f"{report['unmapped_cities']} city value(s) didn't match a known Egyptian city and were kept "
        f"as-is. Check the City column in your raw file if that looks wrong — it's usually a typo "
        f"or a place not yet in the lookup list."
    )
if report["dropped_rows"] > 0:
    st.warning(
        f"{report['dropped_rows']} row(s) were dropped for a missing/invalid date, amount, or product. "
        f"Nothing was guessed to fill the gap."
    )

st.divider()
st.subheader("3. Sales Overview")

total_revenue = df["amount"].sum()
returned_amount = df.loc[df["returned"], "amount"].sum()
net_revenue = total_revenue - returned_amount
aov = df["amount"].mean() if len(df) else 0
overall_return_rate = (df["returned"].sum() / len(df) * 100) if len(df) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"{total_revenue:,.0f}")
k2.metric("Net Revenue", f"{net_revenue:,.0f}")
k3.metric("Avg Order Value", f"{aov:,.0f}")
k4.metric("Overall Return Rate", f"{overall_return_rate:.1f}%")

trend = df.set_index("date").resample("D")["amount"].sum().reset_index()
fig_trend = px.line(trend, x="date", y="amount", title="Revenue Over Time", template="plotly_dark")
st.plotly_chart(fig_trend, use_container_width=True)

cc1, cc2 = st.columns(2)
with cc1:
    prod = df.groupby("product")["amount"].sum().sort_values(ascending=False).reset_index()
    fig_prod = px.bar(prod.head(10), x="amount", y="product", orientation="h",
                       title="Top Products by Revenue", template="plotly_dark")
    fig_prod.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_prod, use_container_width=True)

with cc2:
    city_rev = df.groupby("city_clean")["amount"].sum().reset_index()
    city_rev["lat"] = city_rev["city_clean"].str.lower().map(lambda c: CITY_COORDS.get(c, (None, None))[0])
    city_rev["lon"] = city_rev["city_clean"].str.lower().map(lambda c: CITY_COORDS.get(c, (None, None))[1])
    mapped = city_rev.dropna(subset=["lat", "lon"])
    if len(mapped) >= 2:
        # plotly renamed scatter_mapbox -> scatter_map in newer releases.
        # Support whichever one the deployed environment has.
        if hasattr(px, "scatter_map"):
            fig_map = px.scatter_map(
                mapped, lat="lat", lon="lon", size="amount", color="amount",
                hover_name="city_clean", zoom=4.3, map_style="carto-darkmatter",
                title="Revenue by City"
            )
        else:
            fig_map = px.scatter_mapbox(
                mapped, lat="lat", lon="lon", size="amount", color="amount",
                hover_name="city_clean", zoom=4.3, mapbox_style="carto-darkmatter",
                title="Revenue by City"
            )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        fig_city = px.bar(city_rev.sort_values("amount", ascending=False),
                           x="city_clean", y="amount", title="Revenue by City", template="plotly_dark")
        st.plotly_chart(fig_city, use_container_width=True)

st.divider()
st.subheader("4. Return Risk Alerts")
st.caption("Products flagged when their return rate passes 15%.")

risk = df.groupby("product").agg(orders=("amount", "count"), returns=("returned", "sum")).reset_index()
risk["return_rate_pct"] = (risk["returns"] / risk["orders"] * 100).round(1)
risk["flag"] = risk["return_rate_pct"] > 15
high_risk = risk[risk["flag"]].sort_values("return_rate_pct", ascending=False)

if len(high_risk):
    for _, row in high_risk.iterrows():
        st.markdown(
            f'<span class="high-loss-badge">⚠ HIGH LOSS RISK</span> '
            f'**{row["product"]}** — {row["return_rate_pct"]}% return rate '
            f'({int(row["returns"])} of {int(row["orders"])} orders)',
            unsafe_allow_html=True,
        )
else:
    st.success("No products currently exceed the 15% return-rate threshold.")

st.dataframe(risk.sort_values("return_rate_pct", ascending=False), use_container_width=True)

st.divider()
st.subheader("5. Export Summary")

summary_csv = risk.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV Summary", summary_csv, "executive_summary.csv", "text/csv")

try:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Revenue: {total_revenue:,.0f}", ln=True)
    pdf.cell(0, 8, f"Net Revenue: {net_revenue:,.0f}", ln=True)
    pdf.cell(0, 8, f"Average Order Value: {aov:,.0f}", ln=True)
    pdf.cell(0, 8, f"Overall Return Rate: {overall_return_rate:.1f}%", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "High Loss Risk Products", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if len(high_risk):
        for _, row in high_risk.iterrows():
            pdf.cell(0, 7, f"- {row['product']}: {row['return_rate_pct']}% return rate", ln=True)
    else:
        pdf.cell(0, 7, "None", ln=True)
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    st.download_button("Download PDF Summary", pdf_bytes, "executive_summary.pdf", "application/pdf")
except Exception:
    st.caption("PDF export requires the fpdf2 package (already listed in requirements.txt).")
