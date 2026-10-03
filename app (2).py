
import os
import re
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
from google import genai


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI SQL Analytics",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 700;
    margin-bottom: 5px;
}

.subtitle {
    font-size: 18px;
    opacity: 0.75;
    margin-bottom: 25px;
}

.kpi-card {
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.25);
    text-align: center;
}

.kpi-title {
    font-size: 15px;
    opacity: 0.7;
}

.kpi-value {
    font-size: 28px;
    font-weight: 700;
}

.section-title {
    font-size: 24px;
    font-weight: 650;
    margin-top: 25px;
}

.example-box {
    padding: 12px;
    border-radius: 8px;
    border: 1px solid rgba(128,128,128,0.25);
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# GEMINI API
# =========================================================

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("Gemini API key is not configured.")
    st.info("Add GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)


# =========================================================
# DATABASE
# =========================================================

DB_NAME = "sales.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


# =========================================================
# SQL VALIDATION
# =========================================================

def validate_sql(sql):

    sql = re.sub(
        r"```sql\s*|\s*```",
        "",
        sql,
        flags=re.IGNORECASE
    ).strip()

    if not re.match(r"^SELECT\b", sql, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    statements = [
        x.strip()
        for x in sql.split(";")
        if x.strip()
    ]

    if len(statements) != 1:
        return False, "Multiple SQL statements are not allowed."

    forbidden = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA"
    ]

    for keyword in forbidden:

        if re.search(
            rf"\b{keyword}\b",
            sql,
            re.IGNORECASE
        ):
            return False, f"Forbidden SQL keyword detected: {keyword}"

    return True, "SQL query is safe."


# =========================================================
# GEMINI SQL GENERATION
# =========================================================

def generate_sql(question):

    prompt = f"""
You are a SQL generation assistant.

Database:

Table: sales

Columns:
- sale_date : date
- product   : text
- category  : text
- quantity  : integer
- revenue   : real

User question:
{question}

Generate ONE SQLite SELECT query that answers the question.

Rules:
1. Return ONLY SQL.
2. Use only the sales table.
3. Use only the listed columns.
4. Only SELECT queries are allowed.
5. Do not use INSERT, UPDATE, DELETE, DROP, ALTER,
   CREATE, TRUNCATE, REPLACE, ATTACH, DETACH, or PRAGMA.
6. Do not return Markdown code fences.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    sql = response.text.strip()

    sql = re.sub(
        r"```sql\s*|\s*```",
        "",
        sql,
        flags=re.IGNORECASE
    ).strip()

    return sql


# =========================================================
# SQL EXPLANATION
# =========================================================

def explain_sql(sql):

    prompt = f"""
Explain this SQL query in simple English.

SQL:
{sql}

Explain:
1. What the query does.
2. Which table it uses.
3. What calculation it performs.
4. Why GROUP BY, ORDER BY, or LIMIT are used if present.

Keep the explanation short and beginner-friendly.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    return response.text.strip()


# =========================================================
# SESSION STATE
# =========================================================

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🤖 AI SQL Analytics</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Ask questions in natural language and turn them into '
    'SQL-powered insights.'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# KPI CARDS
# =========================================================

try:

    connection = get_connection()

    stats = pd.read_sql_query(
        """
        SELECT
            SUM(revenue) AS total_revenue,
            SUM(quantity) AS total_quantity,
            COUNT(DISTINCT product) AS products,
            COUNT(DISTINCT category) AS categories
        FROM sales
        """,
        connection
    )

    connection.close()

    total_revenue = stats.loc[0, "total_revenue"]
    total_quantity = stats.loc[0, "total_quantity"]
    total_products = stats.loc[0, "products"]
    total_categories = stats.loc[0, "categories"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">💰 Total Revenue</div>
                <div class="kpi-value">₹{total_revenue:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">📦 Units Sold</div>
                <div class="kpi-value">{total_quantity:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">🛍️ Products</div>
                <div class="kpi-value">{total_products}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">🗂️ Categories</div>
                <div class="kpi-value">{total_categories}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

except Exception:
    pass


st.divider()


# =========================================================
# SAMPLE QUESTIONS
# =========================================================

st.markdown(
    '<div class="section-title">💬 Ask Your Data</div>',
    unsafe_allow_html=True
)

st.write(
    "Try a natural-language question about your sales data."
)

examples = [
    "Show total revenue by category",
    "Which product sold the highest quantity?",
    "Show total revenue by product",
    "Which category generated the most revenue?",
]

selected_example = st.selectbox(
    "Example questions",
    ["Choose an example..."] + examples
)

default_question = (
    selected_example
    if selected_example != "Choose an example..."
    else ""
)

question = st.text_input(
    "Your question",
    value=default_question,
    placeholder="Example: Show total revenue by category"
)

generate_button = st.button(
    "🚀 Generate & Run Query",
    type="primary",
    width="stretch"
)


# =========================================================
# QUERY PROCESSING
# =========================================================

if generate_button:

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        try:

            # ---------------------------------------------
            # Generate SQL
            # ---------------------------------------------

            with st.spinner("🤖 Gemini is generating SQL..."):

                sql = generate_sql(question)

            st.markdown(
                '<div class="section-title">🧠 Generated SQL</div>',
                unsafe_allow_html=True
            )

            st.code(
                sql,
                language="sql"
            )


            # ---------------------------------------------
            # Validate
            # ---------------------------------------------

            valid, message = validate_sql(sql)

            if not valid:

                st.error(
                    f"❌ Query rejected: {message}"
                )

                st.stop()

            st.success(
                "✅ SQL validation passed — safe to execute."
            )


            # ---------------------------------------------
            # Execute
            # ---------------------------------------------

            with st.spinner("🗄️ Running query on database..."):

                connection = get_connection()

                result = pd.read_sql_query(
                    sql,
                    connection
                )

                connection.close()


            st.session_state.last_result = result


            # ---------------------------------------------
            # Result
            # ---------------------------------------------

            st.markdown(
                '<div class="section-title">📋 Query Result</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                result,
                width="stretch"
            )


            # ---------------------------------------------
            # Visualization
            # ---------------------------------------------

            numeric_columns = result.select_dtypes(
                include="number"
            ).columns.tolist()

            if len(result.columns) >= 2 and numeric_columns:

                st.markdown(
                    '<div class="section-title">📊 Visualization</div>',
                    unsafe_allow_html=True
                )

                category_column = result.columns[0]
                value_column = numeric_columns[0]

                fig = px.bar(
                    result,
                    x=category_column,
                    y=value_column,
                    title="Query Result"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )


            # ---------------------------------------------
            # Explanation
            # ---------------------------------------------

            with st.spinner("💡 Generating explanation..."):

                explanation = explain_sql(sql)

            st.markdown(
                '<div class="section-title">💡 SQL Explanation</div>',
                unsafe_allow_html=True
            )

            st.info(explanation)


            # ---------------------------------------------
            # History
            # ---------------------------------------------

            st.session_state.query_history.append({
                "question": question,
                "sql": sql,
                "explanation": explanation
            })

            st.success(
                "🕘 Query added to history."
            )


        except Exception as e:

            st.error(
                f"❌ Something went wrong: {e}"
            )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🕘 Query History")

    if st.session_state.query_history:

        for i, item in enumerate(
            reversed(st.session_state.query_history),
            start=1
        ):

            with st.expander(
                f"Query {i}: {item['question']}"
            ):

                st.write("**SQL**")

                st.code(
                    item["sql"],
                    language="sql"
                )

                st.write("**Explanation**")

                st.write(
                    item["explanation"]
                )

    else:

        st.info(
            "Your previous questions will appear here."
        )

    st.divider()

    st.caption(
        "AI SQL Analytics • Gemini + SQLite + Streamlit"
    )
