import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import datetime

from helpers import apology, login_required, lookup, usd

import operator




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

    maha_total=0
    shares=[]
    user=db.execute("SELECT username,cash FROM users WHERE id=?",session["user_id"])
    company=db.execute("SELECT DISTINCT(symbol) as symbol FROM stocks WHERE id=? AND quantity>0",session["user_id"])
    stock_details=db.execute("SELECT * FROM stocks WHERE id =? ORDER BY date_time desc",session["user_id"])
    for comp in company:
        share=db.execute("SELECT SUM(quantity) as quantity ,stock_name,symbol FROM stocks WHERE symbol =? AND id=? " ,comp["symbol"],session["user_id"])
        price=lookup(comp["symbol"])["price"]
        total=price*share[0]["quantity"]
        share[0]["price"]=price
        share[0]["total"]=round(total,2)
        shares.append(share[0])
    for share in shares:
        maha_total+=share["total"]


    return render_template("index.html",shares=shares,user=user,maha_total=maha_total)


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
            flash("BOUGHT!!")
            return redirect("/")

        # if user dont have sufficient cash to but stocks rendering apology
        return apology("not enough money",403)

    # if user visit it by get method showing him buy page
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    history=[]
    bought=db.execute("SELECT symbol,quantity,price,date_time FROM stocks WHERE id=? AND quantity!=0 ORDER BY date_time",session["user_id"])
    sold=db.execute("SELECT symbol,quantity,price,date_time FROM sold_stocks WHERE id =? AND quantity!=0 ORDER BY date_time",session["user_id"])






    history = bought
    for stock in sold:
        history.append(stock)




    history.sort(key=operator.itemgetter("date_time"))

    return render_template("history.html",history=history)


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
    flash("sucessfully logged out")
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
        flash("REGISTIRED!!")
        return redirect("/")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks_symbol=db.execute("SELECT DISTINCT(symbol) ,quantity FROM stocks WHERE id =? ",session["user_id"] )

    if request.method=="POST":

        option=request.form.get("stocks")
        if not option:
            return apology("enter symbol",400)
        for check  in stocks_symbol:
            if option != check["symbol"]:
                return apology("Choose valid symbol",400)


        count=db.execute("SELECT SUM(quantity) as quantity FROM stocks WHERE symbol =? AND id=?",option,session["user_id"] )

        shares=int(request.form.get("shares"))
        if shares>count[0]["quantity"]:
            return apology("not enough shares",404)

        elif shares<=count[0]["quantity"]:
            share_left=count[0]["quantity"]-shares
            db.execute("UPDATE stocks SET quantity=? WHERE symbol=? AND id=?",share_left,option,session["user_id"] )
            previous_cash=db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])

            cash_returned=shares*(lookup(option)["price"])

            total_cash=cash_returned+previous_cash[0]["cash"]
            db.execute("UPDATE users SET cash=? WHERE id=?",total_cash,session["user_id"])
            db.execute("INSERT INTO sold_stocks(symbol,quantity,price,id) VALUES (?,?,?,?)",option,-shares,lookup(option)["price"],session["user_id"])
            flash("SOLD!!")
            return redirect("/")
       # elif shares==count[0]["quantity"]:
        #    db.execute("DELETE FROM stocks WHERE symbol=? AND id = ?",option,session["user_id"] );
         #   previous_cash=db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])
         #
         #   cash_returned=shares*(lookup(option)["price"])
          #
          #  total_cash=cash_returned+previous_cash[0]["cash"]
           # db.execute("UPDATE users SET cash=? WHERE id=?",total_cash,session["user_id"])
        #    return redirect("/")


    return render_template("sell.html",stocks_symbol=stocks_symbol)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
