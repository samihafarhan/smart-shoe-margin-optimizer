import pandas as pd
import streamlit as st

st.set_page_config(page_title="Shoe Margin Optimizer", layout="wide")


@st.cache_data
def load_data():
    return pd.read_csv("footwear_bom_data.csv")


df = load_data().copy()

st.title("Smart Shoe BOM & Margin Optimizer")
st.caption(
    "Synthetic footwear dataset of 5,000 product lines. Test how cost changes "
    "affect margins and find which products need action."
)

# ---------------- Sidebar controls ----------------
st.sidebar.header("Scenario")
material_increase = st.sidebar.slider("Material cost change (%)", -20, 50, 0)
labor_increase = st.sidebar.slider("Labor cost change (%)", -20, 50, 0)
shipping_increase = st.sidebar.slider("Shipping cost change (%)", -20, 50, 0)
target_margin = st.sidebar.slider("Minimum acceptable margin (%)", 20, 60, 40)

st.sidebar.header("Filters")
categories = st.sidebar.multiselect(
    "Category", sorted(df["Category"].unique()), default=sorted(df["Category"].unique())
)
suppliers = st.sidebar.multiselect(
    "Supplier", sorted(df["Supplier"].unique()), default=sorted(df["Supplier"].unique())
)

# ---------------- Calculations ----------------
df["Base_Cost"] = df["Material_Cost"] + df["Labor_Cost"] + df["Shipping_Cost"]
df["New_Total_Cost"] = (
    df["Material_Cost"] * (1 + material_increase / 100)
    + df["Labor_Cost"] * (1 + labor_increase / 100)
    + df["Shipping_Cost"] * (1 + shipping_increase / 100)
)
df["Old_Margin_%"] = (df["Retail_Price"] - df["Base_Cost"]) / df["Retail_Price"] * 100
df["New_Margin_%"] = (df["Retail_Price"] - df["New_Total_Cost"]) / df["Retail_Price"] * 100

# Price needed to restore the minimum margin, and the matching cost cut
t = target_margin / 100
df["Required_Price"] = df["New_Total_Cost"] / (1 - t)
df["Price_Increase_%"] = (df["Required_Price"] / df["Retail_Price"] - 1) * 100
df["Max_Allowed_Cost"] = df["Retail_Price"] * (1 - t)
df["Cost_Cut_Needed_%"] = (1 - df["Max_Allowed_Cost"] / df["New_Total_Cost"]) * 100

view = df[df["Category"].isin(categories) & df["Supplier"].isin(suppliers)]
at_risk = view[view["New_Margin_%"] < target_margin]
was_at_risk = (view["Old_Margin_%"] < target_margin).sum()

# ---------------- Key findings ----------------
st.subheader("Key findings")
if len(view) == 0:
    st.warning("No products match the current filters.")
    st.stop()

worst_cat = (
    view.groupby("Category")["New_Margin_%"].mean().sort_values().index[0]
)
worst_sup = (
    at_risk.groupby("Supplier").size().sort_values(ascending=False).index[0]
    if len(at_risk)
    else None
)
change = len(at_risk) - was_at_risk
if change > 0:
    trend = f"up from {was_at_risk:,} today"
elif change < 0:
    trend = f"down from {was_at_risk:,} today"
else:
    trend = "no change from today"
st.info(
    f"{len(at_risk):,} of {len(view):,} products ({len(at_risk) / len(view):.1%}) "
    f"fall below the {target_margin}% margin target ({trend}). "
    f"{worst_cat} has the lowest average margin."
    + (f" {worst_sup} supplies the most at-risk products." if worst_sup else "")
)

margin_delta = view["New_Margin_%"].mean() - view["Old_Margin_%"].mean()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Products in view", f"{len(view):,}")
c2.metric("Avg margin today", f"{view['Old_Margin_%'].mean():.1f}%")
c3.metric(
    "Avg margin in scenario",
    f"{view['New_Margin_%'].mean():.1f}%",
    f"{margin_delta:.1f} pts" if abs(margin_delta) >= 0.05 else None,
)
c4.metric(
    "Below target",
    f"{len(at_risk):,}",
    f"{change:+,}" if change != 0 else None,
    delta_color="inverse",
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["At-risk products", "Category & supplier", "Data quality", "About"]
)

# ---------------- Tab 1: at-risk products ----------------
with tab1:
    st.write(
        "Worst margins first. The last two columns show the price increase, or the "
        "cost reduction, that would bring each product back to the target margin."
    )
    cols = [
        "Product_ID", "Category", "Supplier", "Retail_Price", "New_Total_Cost",
        "New_Margin_%", "Required_Price", "Price_Increase_%", "Cost_Cut_Needed_%",
    ]
    table = at_risk.sort_values("New_Margin_%")[cols].round(2)
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button(
        "Download at-risk list (CSV)",
        table.to_csv(index=False).encode("utf-8"),
        file_name="at_risk_products.csv",
        mime="text/csv",
    )

# ---------------- Tab 2: category & supplier ----------------
with tab2:
    left, right = st.columns(2)
    with left:
        st.write("Average margin by category (today vs scenario)")
        cat = view.groupby("Category")[["Old_Margin_%", "New_Margin_%"]].mean().round(2)
        st.bar_chart(cat)
    with right:
        st.write("Supplier summary")
        sup = (
            view.groupby("Supplier")
            .agg(
                Products=("Product_ID", "count"),
                Avg_Material_Cost=("Material_Cost", "mean"),
                Avg_New_Margin=("New_Margin_%", "mean"),
                Below_Target=("New_Margin_%", lambda s: (s < target_margin).sum()),
            )
            .round(2)
            .sort_values("Below_Target", ascending=False)
        )
        st.dataframe(sup, width="stretch")

# ---------------- Tab 3: data quality ----------------
with tab3:
    st.write("Automatic checks on the cost data, to catch discrepancies before analysis.")
    checks = {}
    checks["Missing values"] = int(df[["Material_Cost", "Labor_Cost", "Shipping_Cost", "Retail_Price"]].isna().sum().sum())
    checks["Duplicate Product_IDs"] = int(df["Product_ID"].duplicated().sum())
    checks["Zero or negative costs/prices"] = int(
        (df[["Material_Cost", "Labor_Cost", "Shipping_Cost", "Retail_Price"]] <= 0).any(axis=1).sum()
    )
    checks["Total_Cost does not match Material + Labor + Shipping"] = int(
        ((df["Total_Cost"] - df["Base_Cost"]).abs() > 0.01).sum()
    )
    checks["Gross_Margin_% does not match Retail_Price and Total_Cost"] = int(
        (
            (df["Gross_Margin_%"] - (df["Retail_Price"] - df["Total_Cost"]) / df["Retail_Price"] * 100)
            .abs()
            > 0.5
        ).sum()
    )
    # Material cost outliers vs category median (IQR rule)
    q1 = df.groupby("Category")["Material_Cost"].transform(lambda s: s.quantile(0.25))
    q3 = df.groupby("Category")["Material_Cost"].transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    outlier = (df["Material_Cost"] > q3 + 1.5 * iqr) | (df["Material_Cost"] < q1 - 1.5 * iqr)
    checks["Material cost outliers within category"] = int(outlier.sum())

    result = pd.DataFrame({"Check": checks.keys(), "Rows flagged": checks.values()})
    st.dataframe(result, width="stretch", hide_index=True)
    if outlier.any():
        st.write("Material cost outliers")
        st.dataframe(
            df[outlier][["Product_ID", "Category", "Supplier", "Material_Cost"]].head(50),
            width="stretch",
            hide_index=True,
        )

# ---------------- Tab 4: about ----------------
with tab4:
    st.markdown(
        """
**Purpose:** help product and costing teams see which products lose margin when
material, labor or shipping costs rise, and what price or cost change fixes them.

**Method:** margin = (retail price - total cost) / retail price. Required price =
total cost / (1 - target margin). Cost cut needed = how far total cost must fall
to meet the target at the current retail price.

**Data:** synthetic dataset of 5,000 footwear product lines created for this project.

**Tools:** Python, Pandas, Streamlit. A companion Power BI dashboard covers
cost-driver analysis with a Decomposition Tree.
"""
    )
