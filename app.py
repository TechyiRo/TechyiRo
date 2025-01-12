from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime
import os
from sqlalchemy import desc, func

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///companies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a random secret key
db = SQLAlchemy(app)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    information = db.Column(db.Text, nullable=True)
    person_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    contact_no = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False)  # 'RENT' or 'SELL'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'spit' and password == 'SanRo@2025!':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    app.logger.debug("Rendering index page")
    recent_companies = Company.query.order_by(desc(Company.id)).limit(5).all()
    recent_products = Product.query.order_by(desc(Product.id)).limit(5).all()
    company_count = Company.query.count()
    product_count = Product.query.count()

    # Client details (top 5 countries)
    client_details = db.session.query(Company.country, func.count(Company.id)).group_by(Company.country).order_by(func.count(Company.id).desc()).limit(5).all()

    # Product details (top 5 products)
    product_details = db.session.query(Product.name, func.count(Product.id)).group_by(Product.name).order_by(func.count(Product.id).desc()).limit(5).all()

    # Status details
    status_details = db.session.query(Inventory.status, func.count(Inventory.id)).group_by(Inventory.status).all()

    app.logger.debug(f"Found {company_count} companies and {product_count} products")
    return render_template('index.html', 
                           recent_companies=recent_companies, 
                           recent_products=recent_products, 
                           company_count=company_count, 
                           product_count=product_count,
                           client_details=client_details,
                           product_details=product_details,
                           status_details=status_details)

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        try:
            new_company = Company(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                name=request.form['company_name'],
                address=request.form['company_address'],
                information=request.form['company_information'],
                person_name=request.form['person_name'],
                position=request.form['position'],
                email=request.form['email'],
                contact_no=request.form['contact_no'],
                country=request.form['country']
            )
            db.session.add(new_company)
            db.session.commit()
            return jsonify({"message": "Company registered successfully!"})
        except Exception as e:
            app.logger.error(f"Error registering company: {e}")
            return jsonify({"error": str(e)}), 500
    return render_template('register.html')

@app.route('/companies')
@login_required
def companies():
    try:
        app.logger.info("Fetching all companies")
        all_companies = Company.query.all()
        app.logger.info(f"Found {len(all_companies)} companies")
        return render_template('companies.html', companies=all_companies)
    except Exception as e:
        app.logger.error(f"Error fetching companies: {e}")
        return f"Error: {str(e)}", 500

@app.route('/search')
@login_required
def search():
    query = request.args.get('query', '')
    try:
        results = Company.query.filter(
            (Company.name.ilike(f'%{query}%')) |
            (Company.person_name.ilike(f'%{query}%')) |
            (Company.address.ilike(f'%{query}%')) |
            (Company.contact_no.ilike(f'%{query}%')) |
            (Company.email.ilike(f'%{query}%'))
        ).all()
        return jsonify([{
            'id': company.id,
            'name': company.name,
            'person_name': company.person_name,
            'address': company.address,
            'contact_no': company.contact_no,
            'email': company.email
        } for company in results])
    except Exception as e:
        app.logger.error(f"Error searching companies: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    company = Company.query.get_or_404(id)
    if request.method == 'POST':
        try:
            company.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            company.name = request.form['company_name']
            company.address = request.form['company_address']
            company.information = request.form['company_information']
            company.person_name = request.form['person_name']
            company.position = request.form['position']
            company.email = request.form['email']
            company.contact_no = request.form['contact_no']
            company.country = request.form['country']
            db.session.commit()
            return redirect(url_for('companies'))
        except Exception as e:
            app.logger.error(f"Error updating company: {e}")
            return f"Error: {str(e)}", 500
    return render_template('edit.html', company=company)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    company = Company.query.get_or_404(id)
    try:
        db.session.delete(company)
        db.session.commit()
        return jsonify({"message": "Company deleted successfully!"})
    except Exception as e:
        app.logger.error(f"Error deleting company: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            new_product = Product(
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                name=request.form['product_name'],
                serial_number=request.form['product_sn']
            )
            db.session.add(new_product)
            db.session.commit()
            return jsonify({"message": "Product added successfully!"})
        except Exception as e:
            app.logger.error(f"Error adding product: {e}")
            return jsonify({"error": str(e)}), 500
    return render_template('add_product.html')

@app.route('/products')
@login_required
def products():
    try:
        all_products = Product.query.all()
        all_inventory = db.session.query(
            Inventory,
            Company.name.label('company_name'),
            Product.name.label('product_name'),
            Product.serial_number
        ).join(Company).join(Product).all()
        return render_template('products.html', products=all_products, inventory=all_inventory)
    except Exception as e:
        app.logger.error(f"Error fetching products and inventory: {e}")
        return f"Error: {str(e)}", 500

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        try:
            product.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            product.name = request.form['product_name']
            product.serial_number = request.form['product_sn']
            db.session.commit()
            return redirect(url_for('products'))
        except Exception as e:
            app.logger.error(f"Error updating product: {e}")
            return f"Error: {str(e)}", 500
    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Product deleted successfully!"})
    except Exception as e:
        app.logger.error(f"Error deleting product: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/add_inventory', methods=['GET', 'POST'])
@login_required
def add_inventory():
    if request.method == 'POST':
        try:
            new_inventory = Inventory(
                company_id=request.form['company_id'],
                product_id=request.form['product_id'],
                status=request.form['status']
            )
            db.session.add(new_inventory)
            db.session.commit()
            return jsonify({"message": "Inventory added successfully!"})
        except Exception as e:
            app.logger.error(f"Error adding inventory: {e}")
            return jsonify({"error": str(e)}), 500
    companies = Company.query.all()
    products = Product.query.all()
    return render_template('add_inventory.html', companies=companies, products=products)

@app.route('/chart_data')
@login_required
def chart_data():
    companies = Company.query.order_by(Company.date).all()
    data = {}
    for company in companies:
        month_year = company.date.strftime('%B %Y')
        if month_year in data:
            data[month_year] += 1
        else:
            data[month_year] = 1
    return jsonify(list(data.items()))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5000)

