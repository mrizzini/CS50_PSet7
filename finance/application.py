import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("quote.html")
    # return redirect("/quote")
    # return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        if request.form.get("shares").isdigit():
            if not lookup(request.form.get("symbol")):
                return apology("please input symbol")
            if not request.form.get("shares"):
                return apology("please input amount of shares")

            quote = lookup(request.form.get("symbol"))
            numberOfShares = int(request.form.get("shares"))
            totalPrice = float(numberOfShares * quote["price"])
            stockSymbol = quote["symbol"]
            userId = session["user_id"]

            if type(quote) is dict and numberOfShares > 0:
                cash = db.execute("SELECT cash FROM users WHERE id = :userId", userId=session["user_id"])
                stockExists = db.execute("SELECT * from portfolio WHERE stockSymbol = :symbol and id = :userId", symbol=stockSymbol, userId=session["user_id"])
                userBalance = (cash[0]["cash"])
                if userBalance < totalPrice:
                    return apology("Insufficient funds")
                if len(stockExists) == 1:
                    db.execute("UPDATE portfolio SET shares = shares + :numberOfShares where id = :userId", numberOfShares=numberOfShares, userId=session["user_id"])
                else:
                    db.execute("INSERT INTO portfolio (id, stockSymbol, shares) VALUES(:ID, :stockName, :amountOfShares)", ID=session["user_id"], stockName=stockSymbol, amountOfShares=numberOfShares)
                db.execute("UPDATE users SET cash = cash - :totalPrice WHERE id = :userId", totalPrice=float(numberOfShares * quote["price"]), userId=session["user_id"])
                stockArray = db.execute("SELECT * from portfolio WHERE id = :userId", userId=userId)
                currentPriceArray = []
                for stock in stockArray:
                    currentPriceArray.append(lookup(stock["stockSymbol"]))
                user = db.execute("SELECT * from users WHERE id = :userId", userId=userId)
                completeStockInfo = zip(stockArray, currentPriceArray)
                return render_template("index.html", userInfo = user, priceInfo = completeStockInfo)
            else:
                return apology("invalid input", 400)
        else:
            return apology("invalid input, ints only", 400)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return render_template("history.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        if type(quote) is dict:
            return render_template("quoted.html", stockQuote=quote)
        else:
            return apology("Enter valid stock symbol")

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("missing username", 400)
        if not request.form.get("password"):
            return apology("missing password", 400)
        if not request.form.get("confirmation"):
            return apology("missing password confirmation", 400)
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password does not match confirmation", 400)
        if not db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash=generate_password_hash(request.form.get("password"))):
            return apology("username already taken", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        session["user_id"] = rows[0]["id"]

        return redirect("/", 200)

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    userId = session["user_id"]
    stockArray = db.execute("SELECT * from portfolio WHERE id = :userId", userId=userId)

    if request.method == "POST":
        if request.form.get("shares").isdigit():
            if not lookup(request.form.get("symbol")):
                return apology("please input symbol")
            if not request.form.get("shares"):
                return apology("please input amount of shares")

            quote = lookup(request.form.get("symbol"))
            numberOfShares = int(request.form.get("shares"))
            totalPrice = float(numberOfShares * quote["price"])
            stockSymbol = quote["symbol"]
            sharesUserCurrentlyHas = db.execute("SELECT shares FROM portfolio WHERE id = :userId and stockSymbol = :symbol", userId=userId, symbol = stockSymbol)
            sharesUserCurrentlyHas = sharesUserCurrentlyHas[0]["shares"]

            if sharesUserCurrentlyHas >= numberOfShares:
                db.execute("UPDATE users SET cash = cash + :totalPrice WHERE id = :userId", totalPrice=float(numberOfShares * quote["price"]), userId=session["user_id"])
                db.execute("UPDATE portfolio SET stockSymbol= :symbol, shares= shares - :totalShares WHERE stockSymbol = :symbol and id = :userId", symbol=stockSymbol, totalShares=numberOfShares, userId=session["user_id"])
                if sharesUserCurrentlyHas - numberOfShares == 0:
                    db.execute("DELETE FROM portfolio WHERE stockSymbol = :symbol", symbol=stockSymbol)
                stockArray = db.execute("SELECT * from portfolio WHERE id = :userId", userId=userId)
                currentPriceArray = []
                for stock in stockArray:
                    currentPriceArray.append(lookup(stock["stockSymbol"]))
                user = db.execute("SELECT * from users WHERE id = :userId", userId=userId)
                completeStockInfo = zip(stockArray, currentPriceArray)
                return render_template("index.html", userInfo = user, priceInfo = completeStockInfo)
            else:
                return apology("you do not have enough shares", 400)
        else:
            return apology("invalid input, ints only", 400)
    return render_template("sell.html", stockArray = stockArray)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
