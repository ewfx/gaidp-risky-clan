import streamlit as st
import pandas as pd
from util import read_pdf

# Streamlit App Configuration
st.set_page_config(page_title="AI-Based Data Profiling", page_icon="📄", layout="centered")

st.title("📄 AI-Based Data Profiling")
st.markdown("Upload a PDF file and extract its text for further analysis.")

# File uploader for PDF
uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"], help="Upload a PDF document for text extraction and analysis.")

validator = None

if uploaded_pdf is not None:
    validator = read_pdf(uploaded_pdf)

# File uploader for CSV
uploaded_csv = st.file_uploader("Upload a CSV file", type=["csv"], help="Upload a CSV file for analysis based on extracted PDF content.")

if uploaded_csv is not None:
    df = pd.read_csv(uploaded_csv)
    ret = validator.validate(df)
    # st.subheader("📊 CSV Data Preview:")
    # st.dataframe(df.head())

    # Placeholder for CSV + PDF combined analysis
    st.markdown("---")
    st.subheader("🔍 CSV Analysis")
    st.dataframe(ret[0])

    st.markdown("---")


else:
    st.warning("⚠️ Please upload a CSV file to analyze.")


