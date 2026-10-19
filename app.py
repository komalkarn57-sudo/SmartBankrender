import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import pandas as pd
import numpy as np

app = Flask(__name__)

# Use a strong SECRET_KEY environment variable in production.
app.secret_key = os.environ.get("SECRET_KEY", "local-development-only-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("RENDER") or os.environ.get("VERCEL"):
    app.config["SESSION_COOKIE_SECURE"] = True


# ---------------- DATABASE CONNECTION ----------------
# Set these environment variables in your hosting dashboard:
# DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, and optionally DB_PORT.
# Defaults below are only for local development.
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "smartbank"),
        port=int(os.environ.get("DB_PORT", "3306")),
        connection_timeout=10,
    )


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["POST"])
def register():

    full_name = request.form["full_name"]
    phone = request.form["phone"]
    email = request.form["email"]
    date_of_birth = request.form["date_of_birth"]
    address = request.form["address"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    # Check passwords
    if password != confirm_password:
        flash("Passwords do not match.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if email already exists
    cursor.execute(
        "SELECT * FROM users WHERE email = %s",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        flash("Email already registered.")
        cursor.close()
        conn.close()
        return redirect(url_for("home"))

    # Generate account number
    account_number = str(random.randint(10000000, 99999999))

    # Encrypt password
    password_hash = generate_password_hash(password)

    # Insert user
    query = """
        INSERT INTO users
        (account_number, full_name, email, phone,
         date_of_birth, address, password_hash, balance)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        account_number,
        full_name,
        email,
        phone,
        date_of_birth,
        address,
        password_hash,
        0.00
    )

    cursor.execute(query, values)

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        f"Account created successfully! "
        f"Your account number is {account_number}"
    )

    return redirect(url_for("home"))


# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email = %s",
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and check_password_hash(
        user["password_hash"],
        password
    ):

        session["account_number"] = user["account_number"]

        return redirect(url_for("dashboard"))

    flash("Invalid email or password.")

    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "account_number" not in session:
        return redirect(url_for("home"))

    account_number = session["account_number"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get user information
    cursor.execute(
        "SELECT * FROM users WHERE account_number = %s",
        (account_number,)
    )

    user = cursor.fetchone()

    # Get recent transactions
    cursor.execute(
        """
        SELECT *
        FROM transactions
        WHERE account_number = %s
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (account_number,)
    )

    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        transactions=transactions
    )
# ---------------- DEPOSIT ----------------

@app.route("/deposit", methods=["GET", "POST"])
def deposit():

    # Check whether user is logged in
    if "account_number" not in session:
        return redirect(url_for("home"))

    # Show deposit page
    if request.method == "GET":
        return render_template("deposit.html")

    # Get form data
    amount = request.form.get("amount")
    description = request.form.get("description")

    # Check amount
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        flash("Please enter a valid amount.")
        return redirect(url_for("deposit"))

    if amount <= 0:
        flash("Deposit amount must be greater than zero.")
        return redirect(url_for("deposit"))

    account_number = session["account_number"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # Get current balance
        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE account_number = %s
            """,
            (account_number,)
        )

        user = cursor.fetchone()

        if not user:
            flash("Account not found.")
            return redirect(url_for("dashboard"))

        current_balance = float(user["balance"])

        # Calculate new balance
        new_balance = current_balance + amount


        # Update user's balance
        cursor.execute(
            """
            UPDATE users
            SET balance = %s
            WHERE account_number = %s
            """,
            (new_balance, account_number)
        )


        # Save transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                account_number,
                transaction_type,
                amount,
                description,
                balance_after
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                account_number,
                "Deposit",
                amount,
                description or "Money deposited",
                new_balance
            )
        )


        # Save changes
        conn.commit()

        flash(
            f"₹{amount:.2f} deposited successfully."
        )

        return redirect(url_for("dashboard"))

    except Exception as e:

        conn.rollback()

        flash("Deposit failed. Please try again.")

        print("Deposit Error:", e)

        return redirect(url_for("deposit"))

    finally:

        cursor.close()
        conn.close()
# ---------------- WITHDRAW ----------------

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():

    if "account_number" not in session:
        return redirect(url_for("home"))

    account_number = session["account_number"]

    # Show withdrawal page
    if request.method == "GET":

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE account_number = %s
            """,
            (account_number,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template(
            "withdraw.html",
            user=user
        )

    amount = request.form.get("amount")
    description = request.form.get("description")

    try:
        amount = float(amount)
    except (TypeError, ValueError):

        flash("Please enter a valid amount.")

        return redirect(url_for("withdraw"))

    if amount <= 0:

        flash("Withdrawal amount must be greater than zero.")

        return redirect(url_for("withdraw"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # Get current balance
        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE account_number = %s
            """,
            (account_number,)
        )

        user = cursor.fetchone()

        if not user:

            flash("Account not found.")

            return redirect(url_for("dashboard"))

        current_balance = float(user["balance"])


        # Check sufficient balance
        if amount > current_balance:

            flash("Insufficient balance.")

            return redirect(url_for("withdraw"))


        # Calculate new balance
        new_balance = current_balance - amount


        # Update balance
        cursor.execute(
            """
            UPDATE users
            SET balance = %s
            WHERE account_number = %s
            """,
            (new_balance, account_number)
        )


        # Save transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                account_number,
                transaction_type,
                amount,
                description,
                balance_after
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                account_number,
                "Withdrawal",
                amount,
                description or "Money withdrawn",
                new_balance
            )
        )


        conn.commit()

        flash(
            f"₹{amount:.2f} withdrawn successfully."
        )

        return redirect(url_for("dashboard"))

    except Exception as e:

        conn.rollback()

        print("Withdraw Error:", e)

        flash("Withdrawal failed.")

        return redirect(url_for("withdraw"))

    finally:

        cursor.close()
        conn.close()

# ---------------- TRANSFER ----------------

@app.route("/transfer", methods=["GET", "POST"])
def transfer():

    if "account_number" not in session:
        return redirect(url_for("home"))

    sender_account = session["account_number"]


    # Show transfer page
    if request.method == "GET":

        return render_template("transfer.html")


    receiver_account = request.form.get("receiver_account")
    amount = request.form.get("amount")
    description = request.form.get("description")


    # Check receiver
    if receiver_account == sender_account:

        flash("You cannot transfer money to your own account.")

        return redirect(url_for("transfer"))


    try:

        amount = float(amount)

    except (TypeError, ValueError):

        flash("Please enter a valid amount.")

        return redirect(url_for("transfer"))


    if amount <= 0:

        flash("Transfer amount must be greater than zero.")

        return redirect(url_for("transfer"))


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # Get sender
        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE account_number = %s
            """,
            (sender_account,)
        )

        sender = cursor.fetchone()


        # Get receiver
        cursor.execute(
            """
            SELECT balance
            FROM users
            WHERE account_number = %s
            """,
            (receiver_account,)
        )

        receiver = cursor.fetchone()


        if not sender:

            flash("Sender account not found.")

            return redirect(url_for("dashboard"))


        if not receiver:

            flash("Receiver account does not exist.")

            return redirect(url_for("transfer"))


        sender_balance = float(sender["balance"])


        # Check balance
        if amount > sender_balance:

            flash("Insufficient balance.")

            return redirect(url_for("transfer"))


        new_sender_balance = sender_balance - amount

        new_receiver_balance = float(receiver["balance"]) + amount


        # Update sender
        cursor.execute(
            """
            UPDATE users
            SET balance = %s
            WHERE account_number = %s
            """,
            (
                new_sender_balance,
                sender_account
            )
        )


        # Update receiver
        cursor.execute(
            """
            UPDATE users
            SET balance = %s
            WHERE account_number = %s
            """,
            (
                new_receiver_balance,
                receiver_account
            )
        )


        # Sender transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                account_number,
                transaction_type,
                amount,
                description,
                related_account,
                balance_after
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                sender_account,
                "Transfer Sent",
                amount,
                description or "Money transferred",
                receiver_account,
                new_sender_balance
            )
        )


        # Receiver transaction
        cursor.execute(
            """
            INSERT INTO transactions
            (
                account_number,
                transaction_type,
                amount,
                description,
                related_account,
                balance_after
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                receiver_account,
                "Transfer Received",
                amount,
                description or "Money received",
                sender_account,
                new_receiver_balance
            )
        )


        conn.commit()


        flash(
            f"₹{amount:.2f} transferred successfully."
        )

        return redirect(url_for("dashboard"))


    except Exception as e:

        conn.rollback()

        print("Transfer Error:", e)

        flash("Transfer failed.")

        return redirect(url_for("transfer"))


    finally:

        cursor.close()
        conn.close()
# ---------------- TRANSACTION ANALYSIS ----------------

@app.route("/analysis")
def analysis():

    if "account_number" not in session:
        return redirect(url_for("home"))

    account_number = session["account_number"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            transaction_type,
            amount,
            description,
            related_account,
            balance_after,
            created_at
        FROM transactions
        WHERE account_number = %s
        ORDER BY created_at DESC
        """,
        (account_number,)
    )

    transactions = cursor.fetchall()

    cursor.close()
    conn.close()


    # No transactions
    if not transactions:

        return render_template(
            "analysis.html",
            transactions=[],
            total_transactions=0,
            total_deposit=0,
            total_withdrawal=0,
            total_transfer=0,
            average_transaction=0,
            highest_transaction=0,
            lowest_transaction=0,
            standard_deviation=0
        )


    # Convert transaction data to Pandas DataFrame
    df = pd.DataFrame(transactions)


    # Convert amount column to numbers
    amounts = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )


    # Total transactions
    total_transactions = len(df)


    # Deposits
    deposit_data = df[
        df["transaction_type"] == "Deposit"
    ]

    total_deposit = float(
        deposit_data["amount"].sum()
    )


    # Withdrawals
    withdrawal_data = df[
        df["transaction_type"] == "Withdrawal"
    ]

    total_withdrawal = float(
        withdrawal_data["amount"].sum()
    )


    # Transfers
    transfer_data = df[
        df["transaction_type"].isin(
            ["Transfer Sent", "Transfer Received"]
        )
    ]

    total_transfer = float(
        transfer_data["amount"].sum()
    )


    # NumPy calculations
    average_transaction = float(
        np.mean(amounts)
    )

    highest_transaction = float(
        np.max(amounts)
    )

    lowest_transaction = float(
        np.min(amounts)
    )

    standard_deviation = float(
        np.std(amounts)
    )


    return render_template(
        "analysis.html",

        transactions=transactions,

        total_transactions=total_transactions,

        total_deposit=total_deposit,

        total_withdrawal=total_withdrawal,

        total_transfer=total_transfer,

        average_transaction=average_transaction,

        highest_transaction=highest_transaction,

        lowest_transaction=lowest_transaction,

        standard_deviation=standard_deviation
    )

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)