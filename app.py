from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from hashlib import sha256
from flask_wtf.csrf import CSRFProtect
import uuid

# os environment variables
import os


app = Flask(__name__, static_folder="assets")
app.secret_key = os.urandom(24)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///records.db"
db = SQLAlchemy(app)
login_manager = LoginManager()

login_manager.init_app(app)

csrf = CSRFProtect(app)
csrf.init_app(app)

# Tasks:
# - Add a delete button for transactions
# - Add a filter for transactions
# - Add a search bar for transactions
# - Add a chart for transactions


class Transaction(db.Model):
    id = db.Column(db.String(40), unique=True, primary_key=True, index=True, nullable=False, server_default=str(uuid.uuid4()))

    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'Transaction {self.id}'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'User {self.id}'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)



@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    if not current_user.is_authenticated:
        return redirect('/login')
    transaction_to_edit = db.session.get(Transaction, id)
    if not transaction_to_edit or transaction_to_edit.user_id != current_user.id:
        return redirect('/transactions')
    if request.method == 'POST':
        category = request.form['type']
        date = request.form['date']
        date = datetime.strptime(date, '%m/%d/%Y')
        if date > datetime.now():
            flash('Invalid date (must be behind today\'s date)', 'red')
            return redirect('/')
        # if not valid date, i.e. it is not parsable
        
        amount = request.form['amount']
        if type(amount) is not float:
            try:
                amount = float(amount)
            except:
                flash('Invalid amount', 'red')
                return redirect('/')
        if amount == "0" or float(amount) <= 0:
            flash('Invalid amount', 'red')
            return redirect('/')
        # if not valid amount, i.e. it is not parsable

        description = request.form['description']
        if len(description) > 150:
            flash('Description too long', 'red')
            return redirect('/')
        if category != 'income' and category != 'expense':
            flash('Invalid category', 'red')
            return redirect('/')
        transaction_to_edit.category = category
        transaction_to_edit.date = date
        transaction_to_edit.amount = amount
        transaction_to_edit.description = description
        db.session.commit()
        flash('Transaction edited successfully', 'green')
        return redirect('/transactions')
    transaction_to_edit.date = transaction_to_edit.date.strftime('%m/%d/%Y')
    return render_template('edit.html', transaction=transaction_to_edit)


@app.route('/', methods=['GET', 'POST'])
def index():
    if not current_user.is_authenticated:
        return redirect('/login')
    # all transactions of last 30 days
    todays_date = datetime.now()
    seven_days_ago = todays_date - timedelta(days=7)
    transactions = Transaction.query.filter_by(user_id=current_user.id).filter(Transaction.date >= seven_days_ago).order_by(Transaction.date.asc()).all()
    # find total income and total expense via list comprehension
    total_income = sum([transaction.amount for transaction in transactions if transaction.category == 'income'])
    total_expense = sum([transaction.amount for transaction in transactions if transaction.category == 'expense'])
    current_balance = total_income - total_expense

    # round to 2 decimal places
    total_income = round(total_income, 2)
    total_expense = round(total_expense, 2)
    current_balance = round(current_balance, 2)

    if request.method == 'POST':
        category = request.form['type']
        date = request.form['date']
        date = datetime.strptime(date, '%m/%d/%Y')
        if date > datetime.now():
            flash('Invalid date (must be behind today\'s date)', 'red')
            return redirect('/')
        # if not valid date, i.e. it is not parsable
        
        amount = request.form['amount']
        if type(amount) is not float:
            try:
                amount = float(amount)
            except:
                flash('Invalid amount', 'red')
                return redirect('/')
        if amount == "0" or float(amount) <= 0:
            flash('Invalid amount', 'red')
            return redirect('/')
        # if not valid amount, i.e. it is not parsable

        description = request.form['description']
        if len(description) > 150:
            flash('Description too long', 'red')
            return redirect('/')
        if category != 'income' and category != 'expense':
            flash('Invalid category', 'red')
            return redirect('/')
        new_transaction = Transaction(category=category, date=date, amount=amount, description=description, user_id=current_user.id)
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully', 'green')
        return redirect('/')
    return render_template('home.html', transactions=transactions, total_income=total_income, total_expense=total_expense, current_balance=current_balance)

@app.get('/transactions')
def transactions():
    if not current_user.is_authenticated:
        return redirect('/login')
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.asc()).all()
    # find total income and total expense via list comprehension
    total_income = sum([transaction.amount for transaction in transactions if transaction.category == 'income'])
    total_expense = sum([transaction.amount for transaction in transactions if transaction.category == 'expense'])
    current_balance = total_income - total_expense
    ## round to 2 decimal places
    total_income = round(total_income, 2)
    total_expense = round(total_expense, 2)
    current_balance = round(current_balance, 2)
    return render_template('transactions.html', transactions=transactions, total_income=total_income, total_expense=total_expense, current_balance=current_balance)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        # make sure user exists and password is correct
        if user and user.password == sha256(password.encode()).hexdigest():
            login_user(user)
            return redirect('/')
        return redirect('/login?invalid')
    return render_template('login.html')


@app.route('/delete/<int:id>')
def delete(id):
    if not current_user.is_authenticated:
        return redirect('/login')
    transaction_to_delete = db.session.get(Transaction, id)
    if not transaction_to_delete or transaction_to_delete.user_id != current_user.id:
        return redirect('/transactions')
    db.session.delete(transaction_to_delete)
    db.session.commit()
    return redirect('/transactions')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # if username already exists, return error
        if User.query.filter_by(username=username).first():
            return redirect('/register?usernameExists')
        # encrypt password
        password = sha256(password.encode()).hexdigest()
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login?accountCreated')
    return render_template('register.html')

if __name__ == '__main__':
    app.run(host=0.0.0.0)