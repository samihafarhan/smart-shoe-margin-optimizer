import streamlit as st
import pandas as pd

# Set up the page
st.set_page_config(page_title="Margin Optimizer", layout="wide")
st.title("Shoe Margin Optimizer")

# Load the data we made earlier
df = pd.read_csv('footwear_bom_data.csv')

# Make a sidebar with sliders for the user to play with
st.sidebar.header("Change the Costs")
st.sidebar.write("See what happens if supplier prices go up:")
material_increase = st.sidebar.slider("Material Cost Increase (%)", 0, 50, 0)
labor_increase = st.sidebar.slider("Labor Cost Increase (%)", 0, 50, 0)

# Do the math based on the sliders
df['New_Material'] = df['Material_Cost'] * (1 + (material_increase / 100))
df['New_Labor'] = df['Labor_Cost'] * (1 + (labor_increase / 100))
df['New_Total_Cost'] = df['New_Material'] + df['New_Labor'] + df['Shipping_Cost']

# Calculate the new profit margin
df['New_Margin_%'] = (((df['Retail_Price'] - df['New_Total_Cost']) / df['Retail_Price']) * 100).round(2)

# Show the big numbers at the top
col1, col2 = st.columns(2)
col1.metric("Old Average Margin", f"{df['Gross_Margin_%'].mean():.2f}%")
col2.metric("New Average Margin", f"{df['New_Margin_%'].mean():.2f}%")

# Show a warning if margins drop too low
low_margin_count = len(df[df['New_Margin_%'] < 40])
st.error(f"Warning: {low_margin_count} shoes now have a profit margin below 40%.")

# Show the updated list of shoes
st.write("Updated Shoe List:")
st.dataframe(df[['Product_ID', 'Category', 'Supplier', 'Retail_Price', 'New_Total_Cost', 'New_Margin_%']].head(15))