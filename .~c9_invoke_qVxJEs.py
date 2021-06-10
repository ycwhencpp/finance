import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import datetime

from helpers import apology, login_required, lookup, usd

users=[]


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

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
   # stock_details=db.execute("SELECT stock_name,SUM(quantiy) as shares FROM stocks WHERE id =? GROUP BY stock_name HAVING shares>0",session["user_id"])
   # user=db.execute("SELECT username FROM users WHERE id=?",session["user_id"])
    #grand_total=0
    #for record in stock_details:
     #   stock=lookup(record["symbol"])



    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    #checking if the user is visting the route after filling the form or not

    if request.method=="POST":
        #getting values of stock name from input field

        symbol=request.form.get("symbol")

        #checking whether user have provided the symbol or not
        if not symbol:
            return apology("provide the symbol",403)

        # checking whether user have provided the correct symbol or not
        if  lookup(symbol)==None:
            return apology("incorrect symbol",404)

        #getting values of amount from input filed
        shares=request.form.get("shares")

        #checking whether the user has provided the quantity or not
        if not shares :
            return apology("provide the quantity",403)

        #using lookup() for  checking the current price of stocks (lookup function returns dict)
        stock_price=lookup(symbol)["price"]


        # checking the cash user have in his wallet
        user_cash=db.execute("SELECT cash FROM users where (id) IN (?)",session["user_id"])

        # now checking wether the user have appropriate balace to but the stock or not
        # user_cash[0]["cash"]=>the value of cash not a list containg dict
        if user_cash[0]["cash"] >= (stock_price *int(shares)):

            # inserting the stock price,quantity,date an dtime at which stocks have been bought and user id too
            db.execute("INSERT INTO stocks (id ,stock_name,price,quantity,symbol) VALUES (?,?,?,?,?)",session["user_id"],lookup(symbol)["name"],lookup(symbol)["price"],shares,symbol)


            # keeping count of cash left in user account after purchaisng stocks
            cash_left= user_cash[0]["cash"]-(stock_price * int(shares))

            # updating the value of remaining balance in users wallet
            db.execute("UPDATE users SET cash = ? WHERE id = ?",round(float(cash_left),2),session["user_id"])

            #after succesful purcahse redirecting him to index page
            return redirect("/")

        # if user dont have sufficient cash to but stocks rendering apology
        return apology("not enough money",403)

    # if user visit it by get method showing him buy page
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))


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
    if request.method=="GET":
        return render_template("quote.html")
    symbol=request.form.get("symbol")
    return render_template("quoted.html",symbol=lookup(symbol))

users=db.execute("SELECT username FROM users")

print(users)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method=="POST":
        username=request.form.get("username")

        if not username :
            return apology("Insert username",403)

        row = db.execute("SELECT count(*) FROM users WHERE username = ?",username)
        if row ==1:
            return apology("Username not available",403)

        password=request.form.get("password")
        confirmation=request.form.get("confirmation")

        if not password :
            return apology("Insert password",403)
        elif  password!=confirmation:
            return apology("Password did not matched",403)

        password_hash=generate_password_hash(password)
        db.execute("INSERT INTO users(username,hash) VALUES (?,?)",username,password_hash)
        return redirect("/")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks_symbol=db.execute("SELECT DISTINCT(symbol) FROM stocks WHERE id =? ",session["user_id"] )
    print(stocks_symbol)
    if request.method=="POST":

        option=request.form.get("stocks")
        if not option:
            return apology("enter symbol",400)
        for check in stocks_symbol:
            if option not in check["symbol"]:
                return apology("Choose valid symbol",400)

        count=db.execute("SELECT SUM(quantity) as quantity FROM stocks WHERE symbol =? AND id=?",option,session["user_id"] )
        print(count)
        shares=int(request.form.get("shares"))
        if shares>count[0]["quantity"]:
            return apology("not enough shares",404)
        if shares<count[0]["quantity"]:
            share_left=count[0]["quantity"]-shares
            db.execute("UPDATE stocks SET quantity=? WHERE symbol=? AND id=?",share_left,option,session["user_id"] )
            return redirect("/")
        if shares==count[0]["quantity"]:
            db.execute("DELETE FROM stocks WHERE symbol=? AND id = ?",option,session["user_id"] );
            return redirect("/")
        cash




    return render_template("sell.html",stocks_symbol=stocks_symbol)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
