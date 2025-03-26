import streamlit as st
import pandas as pd
import openai
import faiss
import numpy as np
from util import extract_text
from validator import DynamicValidator
import time

# ✅ Initialize OpenAI API Key
openai.api_key = ""  # Replace with your OpenAI API key

# ✅ Streamlit UI
st.set_page_config(page_title="AI-Based Data Profiling", page_icon="📄", layout="centered")
st.title("📄 AI-Based Data Profiling")
st.markdown("Upload a PDF file and CSV file for validation.")

# ✅ OpenAI Embedding Function (Batch Processing)
def get_embeddings(text_list):
    """Generate OpenAI embeddings for a list of text inputs."""
    if not isinstance(text_list, list):
        raise ValueError("❌ Error: `text_list` must be a list of strings.")

    text_list = [str(text).strip() for text in text_list if isinstance(text, str) and text.strip()]

    if not text_list:
        print("⚠️ Warning: `text_list` is empty after filtering. Skipping embedding request.")
        return []

    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text_list[:10]  # ✅ Limit batch size to avoid API limits
        )
        return [embedding_record.embedding for embedding_record in response.data] if response.data else []

    except openai.BadRequestError as e:
        print(f"❌ OpenAI BadRequestError: {e}")
        return []
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return []

# 📌 Step 1: Upload PDF
uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"])

pdf_rules = []
faiss_index = None

if uploaded_pdf is not None:
    pdf_text = extract_text(uploaded_pdf)  # Extract text from the PDF
    st.success("✅ PDF text extracted successfully!")

    # ✅ Extract rules from PDF (assuming rules are structured)
    pdf_sentences = pdf_text.split("\n")  # Split into sentences
    pdf_rules = [s.strip() for s in pdf_sentences if s.strip() and "must" in s.lower()]  # Filter rule-based text

    if not pdf_rules:
        st.error("❌ No valid rules extracted from the PDF.")
    else:
        pdf_embeddings = np.array(get_embeddings(pdf_rules)).astype("float32")  # ✅ Batch embeddings

        if pdf_embeddings.size == 0:
            st.error("❌ OpenAI failed to generate embeddings. Check API key and input format.")
        else:
            faiss_index = faiss.IndexFlatL2(len(pdf_embeddings[0]))  # ✅ Create FAISS index
            faiss_index.add(pdf_embeddings)
            st.success("✅ FAISS vector database created for extracted rules!")

# 📌 Step 2: Upload CSV for Validation
uploaded_csv = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_csv is not None and faiss_index is not None:
    df = pd.read_csv(uploaded_csv)
    st.success("✅ CSV file uploaded successfully!")

    # ✅ Function to Match CSV Columns with PDF Rules
    def match_rule(column_name):
        """Finds the closest matching rule for a given column using FAISS search."""
        column_embedding = np.array(get_embeddings([column_name])).astype("float32")

        if column_embedding.size == 0:
            print(f"⚠️ Warning: No embedding generated for '{column_name}', skipping FAISS search.")
            return "No matching rule found"

        _, closest_match_index = faiss_index.search(column_embedding.reshape(1, -1), 1)

        if closest_match_index[0][0] == -1:
            print(f"⚠️ No match found for column '{column_name}' in FAISS index.")
            return "No matching rule found"
        
        return pdf_rules[closest_match_index[0][0]]  # ✅ Return matched rule

    # ✅ Match CSV Columns with Extracted Rules
    matched_rules = {col: match_rule(col) for col in df.columns}
    matched_df = pd.DataFrame(list(matched_rules.items()), columns=["CSV Column", "Matched PDF Rule"])

    st.subheader("🔍 Matched Rules for CSV Columns")
    st.dataframe(matched_df)

    # ✅ Call the Validator
    validator = DynamicValidator(df)
    #validation_results, failure_log = validator.validate(df)
    ret = validator.validate(df)
    # ✅ Display Validation Results
    st.subheader("📊 CSV Validation Results")
    st.dataframe(ret[0])

    '''if not failure_log.empty:
        st.subheader("❌ Validation Failures")
        st.dataframe(failure_log)
        st.warning("⚠️ Some fields failed validation. Check the failures above.")
    else:
        st.success("✅ All fields passed validation!")'''

elif uploaded_csv is not None:
    st.error("❌ Please upload a PDF first to extract validation rules.")

else:
    st.warning("⚠️ Please upload a CSV file to analyze.")
