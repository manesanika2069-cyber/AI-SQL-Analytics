
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
# GEMINI API KEY
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

    # Remove Markdown code fences
    sql = re.sub(
        r"```sql\s*|\s*```",
        "",
        sql,
        flags=re.IGNORECASE
    ).strip()

    # Must start with SELECT
    if not re.match(r"^SELECT\b", sql, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # Only one SQL statement
    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
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
# GENERATE SQL
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
# EXPLAIN SQL
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
# QUERY HISTORY
# =========================================================

if "query_history" not in st.session_state:
    st.session_state.query_history = []


# =========================================================
# HEADER
# =========================================================

st.title("🤖 AI SQL Analytics")

st.write(
    "Ask questions about your sales data using natural language."
)


# =========================================================
# QUESTION INPUT
# =========================================================

question = st.text_input(
    "Ask your question",
    placeholder="Example: Show total revenue by category"
)

generate_button = st.button(
    "🚀 Generate & Run Query",
    type="primary"
)


# =========================================================
# MAIN PROCESS
# =========================================================

if generate_button:

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        try:

            # ---------------------------------------------
            # Generate SQL
            # ---------------------------------------------

            with st.spinner("Generating SQL with Gemini..."):

                sql = generate_sql(question)

            st.subheader("🧠 Generated SQL")

            st.code(
                sql,
                language="sql"
            )


            # ---------------------------------------------
            # Validate SQL
            # ---------------------------------------------

            valid, validation_message = validate_sql(sql)

            if not valid:

                st.error(
                    f"SQL rejected ❌ — {validation_message}"
                )

                st.stop()

            st.success(
                "SQL validation passed ✅"
            )


            # ---------------------------------------------
            # Execute SQL
            # ---------------------------------------------

            with st.spinner("Running query..."):

                connection = get_connection()

                result = pd.read_sql_query(
                    sql,
                    connection
                )

                connection.close()


            # ---------------------------------------------
            # Result
            # ---------------------------------------------

            st.subheader("📋 Query Result")

            st.dataframe(
                result,
                use_container_width=True
            )


            # ---------------------------------------------
            # Explanation
            # ---------------------------------------------

            with st.spinner("Generating SQL explanation..."):

                explanation = explain_sql(sql)

            st.subheader("💡 SQL Explanation")

            st.info(explanation)


            # ---------------------------------------------
            # Visualization
            # ---------------------------------------------

            numeric_columns = result.select_dtypes(
                include="number"
            ).columns.tolist()

            if len(result.columns) >= 2 and numeric_columns:

                st.subheader("📊 Visualization")

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
                    use_container_width=True
                )


            # ---------------------------------------------
            # Save History
            # ---------------------------------------------

            st.session_state.query_history.append({
                "question": question,
                "sql": sql,
                "explanation": explanation
            })

            st.success(
                "Query saved to history 🕘"
            )


        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )


# =========================================================
# SIDEBAR — QUERY HISTORY
# =========================================================

st.sidebar.title("🕘 Query History")

if st.session_state.query_history:

    for i, item in enumerate(
        reversed(st.session_state.query_history),
        start=1
    ):

        with st.sidebar.expander(
            f"Query {i}: {item['question']}"
        ):

            st.write("**SQL:**")

            st.code(
                item["sql"],
                language="sql"
            )

            st.write("**Explanation:**")

            st.write(
                item["explanation"]
            )

else:

    st.sidebar.info(
        "No queries yet."
    )
