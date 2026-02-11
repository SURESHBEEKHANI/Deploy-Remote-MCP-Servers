from fastmcp import FastMCP
import os
import sqlite3

# Paths
DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

# Initialize MCP
mcp = FastMCP("ExpenseTracker")

# Initialize Database
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

init_db()

# -------------------------
# MCP Tools
# -------------------------

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = "SELECT category, SUM(amount) AS total_amount FROM expenses WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def delete_expense(expense_id):
    '''Delete an expense entry by ID.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cur.rowcount:
            return {"status": "ok", "deleted_id": expense_id}
        else:
            return {"status": "error", "message": "Expense not found"}

@mcp.tool()
def update_expense(expense_id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''Update fields of an existing expense entry.'''
    with sqlite3.connect(DB_PATH) as c:
        fields = []
        params = []
        if date is not None:
            fields.append("date = ?")
            params.append(date)
        if amount is not None:
            fields.append("amount = ?")
            params.append(amount)
        if category is not None:
            fields.append("category = ?")
            params.append(category)
        if subcategory is not None:
            fields.append("subcategory = ?")
            params.append(subcategory)
        if note is not None:
            fields.append("note = ?")
            params.append(note)
        
        if not fields:
            return {"status": "error", "message": "No fields provided to update"}

        params.append(expense_id)
        query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"
        cur = c.execute(query, params)
        if cur.rowcount:
            return {"status": "ok", "updated_id": expense_id}
        else:
            return {"status": "error", "message": "Expense not found"}

@mcp.tool()
def total_expenses(start_date, end_date):
    '''Calculate total expenses within a date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        )
        total = cur.fetchone()[0] or 0
        return {"total": total}

# -------------------------
# MCP Resources
# -------------------------

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------
# Run MCP Server
# -------------------------
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000        # Change this to any port you want
    )
