import streamlit as st
import pandas as pd

# Set page layout to wide for better chart viewing
st.set_page_config(page_title="Ingestion Telemetry", layout="wide")

st.title("Enterprise RAG: Ingestion Benchmarks")

# Load the CSV. The @st.cache_data decorator ensures it reads fast.


@st.cache_data(ttl=5)  # Refreshes every 5 seconds if live-updating
def load_data():
    try:
        df = pd.read_csv("ingestion_benchmarks.csv", on_bad_lines="skip")
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


df = load_data()

if df.empty:
    st.warning("Waiting for ingestion_benchmarks.csv to populate...")
else:
    # --- Top-Level Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Documents Processed", f"{len(df):,}")
    col2.metric("Total Chunks Generated", f"{df['num_chunks'].sum():,}")
    col3.metric("Avg Partition Time (s)",
                f"{df['partition_time_s'].mean():.2f}s")
    col4.metric("Avg Embedding Time (s)",
                f"{df['embedding_time_s'].mean():.2f}s")

    st.markdown("---")

    # --- Interactive Charts ---
    colA, colB = st.columns(2)

    with colA:
        st.subheader("CPU Load: File Size vs. Partition Time")
        st.caption("Validates the linear scaling of the Unstructured NLP engine.")
        # Native Streamlit scatter chart
        st.scatter_chart(
            data=df,
            x="file_size_bytes",
            y="partition_time_s",
            color="#ff4b4b"
        )

    with colB:
        st.subheader("Network Load: Embedding API Latency")
        st.caption("Validates the stability of OpenAI TPM limits.")
        # Native Streamlit line chart
        st.line_chart(
            data=df,
            y="embedding_time_s",
            color="#0068c9"
        )

    st.markdown("---")
    st.subheader("Raw Telemetry Data")
    # Show latest 100 files
    st.dataframe(df.tail(100), width="stretch")
