import os
from flask import Flask, request, jsonify,render_template,redirect,url_for,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from sqlalchemy import func
from wtforms import StringField, FloatField, DateField, FileField, SelectField,SubmitField,IntegerField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename
import secrets
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import requests 
import re  # Import the regular expressions module
from collections import defaultdict





app = Flask(__name__)
app.secret_key = 'anish_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///mydatashop.sqlite3"
db = SQLAlchemy(app)
ma = Marshmallow(app)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref='users')
    cart = db.relationship('Cart', backref='user', lazy=True)
    shopping_lists = db.relationship('ShoppingList', backref='user', lazy=True, cascade="all, delete-orphan")
    

    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), default='default.jpg')
    products = db.relationship('Product', backref='category_ref', lazy=True, cascade="all, delete-orphan")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manufacture_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    rate_per_unit = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    image = db.Column(db.String(255),default ='default.jpg')
    cart_items_product = db.relationship('CartItem', backref='product_ref', lazy=True,cascade="all, delete-orphan")
    shopping_lists = db.relationship('ShoppingList', backref='product_ref_shopinglist', lazy=True,cascade="all, delete-orphan")
   
    
    
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('CartItem', backref='cart', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='cart_items')

class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    checkout_date = db.Column(db.DateTime, nullable=True)  # Add a new column for checkout date
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_rate_per_unit = db.Column(db.Float, nullable=False)
    product = db.relationship('Product', backref='shop_item')
   

migrate = Migrate(app, db)

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[InputRequired()])
    image = FileField('Category Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[InputRequired()])
    rate_per_unit = FloatField('Rate per Unit', validators=[InputRequired()])
    stock_quantity = IntegerField('No of Item',validators=[InputRequired()])
    manufacture_date = DateField('Manufacture Date', validators=[InputRequired()])
    expiry_date = DateField('Expiry Date', validators=[InputRequired()])
    image = FileField('Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    category_id = SelectField('Category', coerce=int, validators=[InputRequired()])
    submit = SubmitField('Create Product')

def save_uploaded_file(file):
    if file:
        random_hex = secrets.token_hex(8)
        _, file_extension = os.path.splitext(file.filename)
        unique_filename = random_hex + file_extension
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        return unique_filename
    return None
    



class CategorySchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'image')

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)


class ProductSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name','ManufactureDate','ExpDate','rate','quantity','CategoryId', 'image')

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

##apis

# Create a new category
@app.route('/api/categories', methods=['POST'])
def create_category():
    name = request.form.get('name')
    image_file = request.files.get('image')

    # Check if a category with the same name already exists
    existing_category = Category.query.filter_by(name=name).first()
    if existing_category:
        return jsonify({'message': 'A category with this name already exists.'}), 400

    # Save the uploaded image and get the file path
    if image_file:
        filename = secure_filename(image_file.filename)
        image_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_filepath)
    else:
        # If no image is provided, you can set a default image path or handle it as needed
        image_filepath = 'default.jpg'

    # Create a new category
    new_category = Category(name=name, image=image_filepath)

    # Add the new category to the database
    db.session.add(new_category)
    db.session.commit()

    return category_schema.jsonify(new_category), 201



# Get all categories
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return categories_schema.jsonify(categories)

# Get a specific category by ID
@app.route('/api/categories/<int:id>', methods=['GET'])
def get_category(id):
    category = Category.query.get(id)
    if category is None:
        return jsonify({'message': 'Category not found'}), 404
    return category_schema.jsonify(category)


# Update a category by ID

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    category = Category.query.get_or_404(id)
    name = request.form.get('name')
    image_file = request.files.get('image')

    # Check if a category with the same name already exists
    existing_category = Category.query.filter(Category.name == name, Category.id != id).first()
    if existing_category:
        return jsonify({'message': 'A category with this name already exists.'}), 400

    # If a new image file is provided, remove the old image file
    if image_file:
        if category.image != 'default.jpg':
            # Delete the old image file
            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        # Save the uploaded image and get the file path
        filename = secure_filename(image_file.filename)
        image_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_filepath)
    else:
        # If no image is provided, keep the existing image path
        image_filepath = category.image

    category.name = name
    category.image = image_filepath

    db.session.commit()

    return category_schema.jsonify(category)


# Delete a category by ID
@app.route('/api/categories/<int:id>', methods=['DELETE'])
def remove_category(id):
    category = Category.query.get_or_404(id)
    image_path = category.image
    
    # Remove associated products and their images
    for product in category.products:
        # Delete the product's image file
        if product.image != 'default.jpg':
            product_image_path = product.image
            product_image_filename = os.path.basename(product_image_path)
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product_image_filename))
        
        # Delete the product from the database
        db.session.delete(product)
    
    # Remove the associated image file for the category
    if category.image != 'default.jpg':
        image_filename = os.path.basename(image_path)
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
    
    # Delete the category from the database
    db.session.delete(category)
    db.session.commit()
    
    return '', 204


# Create a new product
@app.route('/api/products', methods=['POST'])
def create_product():
    name = request.form.get('name')
    manufacture_date = request.form.get('manufacture_date')
    expiry_date = request.form.get('expiry_date')
    rate_per_unit = request.form.get('rate_per_unit')
    stock_quantity = request.form.get('stock_quantity')
    category_id = request.form.get('category_id')
    image_file = request.files.get('image')

    existing_product = Product.query.filter_by(name=name).first()
    if existing_product:
        return jsonify({'message': 'A product with this name already exists.'}), 400
    
    if image_file:
        unique_filename = None
        random_hex = secrets.token_hex(8)
        _, file_extension = os.path.splitext(image_file.filename)
        unique_filename = random_hex + file_extension
        image_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image_file.save(image_filepath)
    else:
        # If no image is provided, you can set a default image path or handle it as needed
        image_filepath = 'default.jpg'

    manufacture_date = datetime.strptime(manufacture_date, '%Y-%m-%d').date()
    expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    new_product = Product(
        name=name,
        manufacture_date=manufacture_date,
        expiry_date=expiry_date,
        rate_per_unit=rate_per_unit,
        stock_quantity=stock_quantity,
        category_id=category_id,
        image=image_filepath
    )
    db.session.add(new_product)
    db.session.commit()
    
    return product_schema.jsonify(new_product), 201

# Get all products
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return products_schema.jsonify(products)

# Get a specific product by ID
@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    product = Product.query.get_or_404(id)
    return product_schema.jsonify(product)

# Update a product by ID
@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    name = request.form.get('name')
    manufacture_date = request.form.get('manufacture_date')
    expiry_date = request.form.get('expiry_date')
    rate_per_unit = request.form.get('rate_per_unit')
    stock_quantity = request.form.get('stock_quantity')
    category_id = request.form.get('category_id')
    image_file = request.files.get('image')
    # Update product attributes based on request data
    existing_product = Product.query.filter(Product.name == name, Product.id != id).first()
    if existing_product:
        return jsonify({'message': 'A Product with this name already exists.'}), 400
     # If a new image file is provided, remove the old image file
    if image_file:
        if product.image != 'default.jpg':
            # Delete the old image file
            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        # Save the uploaded image and get the file path
        unique_filename = None
        random_hex = secrets.token_hex(8)
        _, file_extension = os.path.splitext(image_file.filename)
        unique_filename = random_hex + file_extension
        image_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image_file.save(image_filepath)
        
    else:
        # If no image is provided, keep the existing image path
        image_filepath = product.image
    manufacture_date = datetime.strptime(manufacture_date, '%Y-%m-%d').date()
    expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    product.name = name
    product.manufacture_date = manufacture_date
    product.expiry_date = expiry_date
    product.rate_per_unit = rate_per_unit
    product.stock_quantity = stock_quantity
    product.category_id = category_id
    product.image = image_filepath
    
    db.session.commit()
    
    return product_schema.jsonify(product)

# Delete a product by ID
@app.route('/api/products/<int:id>', methods=['DELETE'])
def remove_product(id):
    product = Product.query.get_or_404(id)
    image_path = product.image
    
    if product.image != 'default.jpg':
        image_filename = os.path.basename(image_path)
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
    
    # Delete the category from the database
    db.session.delete(product)
    db.session.commit()
    
    return '', 204


##routes foe web app

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    # Admin login route logic
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.role.name == 'Admin' and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard route

        flash('Invalid username or password', 'danger')  # Display error message
        return render_template('admin_login.html')

    return render_template('admin_login.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    # User login route logic
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.role.name == 'User' and user.check_password(password):
            login_user(user)
            return redirect(url_for('user_dashboard'))  # Redirect to user dashboard route

        flash('Invalid username or password', 'danger')  # Display error message

    return render_template('user_login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if the username or password fields are empty
        if not username or not password:
            flash('Username and password are required.','danger')
        else:
            # Check if the username is already taken
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different username.','danger')
            else:
                # Password validation rules
                if len(password) < 5:
                    flash('Password must be at least 5 characters long.', 'danger')
                elif not re.search(r'[A-Z]', password):
                    flash('Password must contain at least one capital letter.', 'danger')
                elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    flash('Password must contain at least one special character.', 'danger')
                elif not re.search(r'[A-Z]', password) and  not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    flash('Password must contain at least one capital letter and Password must contain at least one special character','danger')
                else:
                    user_role = Role.query.filter_by(name='User').first()
                    if not user_role:
                        user_role = Role(name='User')
                        db.session.add(user_role)
                        db.session.commit()

                    new_user = User(username=username)
                    new_user.set_password(password)
                    new_user.role = user_role

                    db.session.add(new_user)
                    db.session.commit()

                    flash('Registration successful. You can now log in.', 'success')
                    return redirect(url_for('user_login'))

    return render_template('register.html')



@app.route('/logout', methods=['POST'])
@login_required
def logout():
    user_role = current_user.role.name if current_user.is_authenticated else None

    logout_user()
    flash('You have been logged out.', 'danger')

    if user_role == 'Admin':
        return redirect(url_for('admin_login'))  # Redirect admin to admin login
    else:
        return redirect(url_for('user_login'))  # Redirect user to user login

'''
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role.name == 'Admin':
        # Use the API to get categories and products
        categories_response = requests.get('http://localhost:5000/api/categories')
        products_response = requests.get('http://localhost:5000/api/products')
        
        if categories_response.status_code == 200 and products_response.status_code == 200:
            categories = categories_response.json()
            products = products_response.json()
            
            # Implement admin dashboard logic here, passing categories and products to the template
            return render_template('admin_dashboard.html', categories=categories, products=products)
        else:
            # Handle API request errors
            flash('Error retrieving data from the API', 'error')
            return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_login'))

@app.route('/admin_dashboard/search', methods=['POST'])
@login_required
def admin_dashboard_search():
    categories1 = requests.get('http://localhost:5000/api/categories')
    products1 = requests.get('http://localhost:5000/api/products')
    search_type = request.form.get('search_type')
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

    return render_template('admin_dashboard_search.html', categories=categories, products=products,categories1=categories1,products1=products1,os=os)


@app.route('/admin_category/search', methods=['POST'])
@login_required
def admin_category_search():
    categories1 = requests.get('http://localhost:5000/api/categories')
    products1 = requests.get('http://localhost:5000/api/products')
    search_type = 'category'
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        

    return render_template('admin_category_search.html', categories=categories,categories1=categories1,products1=products1,os=os)

@app.route('/admin_product/search', methods=['POST'])
@login_required
def admin_product_search():
    categories1 = requests.get('http://localhost:5000/api/categories')
    products1 = requests.get('http://localhost:5000/api/products')
    search_type = 'product'
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

    return render_template('admin_product_search.html', categories=categories, products=products,categories1=categories1,products1=products1,os=os)




@app.route('/admin/categories')
@login_required
def admin_categories():
    # Make an HTTP GET request to your API endpoint that retrieves categories
    api_url = 'http://localhost:5000/api/categories'  # Replace with your actual API URL
    response = requests.get(api_url)

    if response.status_code == 200:
        categories = response.json()
        return render_template('admin_categories.html', categories=categories, os=os)
    else:
        flash('Failed to fetch categories from the API.','danger')
      


@app.route('/admin/products', methods=['GET'])
@login_required
def admin_products():
    # Make an HTTP GET request to your API endpoint that retrieves products
    api_url = 'http://localhost:5000/api/products'  # Replace with your actual API URL
    response_products = requests.get(api_url)

    if response_products.status_code == 200:
        products = response_products.json()
        api_url = 'http://localhost:5000/api/categories'  # Replace with your actual API URL
        response_categories = requests.get(api_url)

        if response_categories.status_code == 200:
            categories = response_categories.json() 
            return render_template('admin_products.html', categories=categories, products=products, os=os)
    else:
        flash('Failed to fetch products from the API.', 'danger')
       


@app.route('/admin/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        name = form.name.data.strip()  # Remove leading/trailing whitespaces
        image_file = form.image.data
        data = {'name': name}
        # Convert the input name to lowercase
        name_lower = name.lower()
        existing_category = Category.query.filter(func.lower(Category.name) == name_lower).first()
        if existing_category:
            flash('Category with the same name already exists', 'danger')
        else:
            unique_filename = None  # Initialize with None
            if image_file:
                # Generate a unique filename
                random_hex = secrets.token_hex(8)
                _, file_extension = os.path.splitext(image_file.filename)
                unique_filename = random_hex + file_extension
        
                files = {'image': (unique_filename, image_file.read())}  # Use the image file object directly
            else:
                files=None

        response = requests.post('http://localhost:5000/api/categories', data=data, files=files)
                

        if response.status_code == 201:
            flash('Category added successfully.', 'success')
            return redirect(url_for('admin_categories'))  # Redirect to the categories list page after adding a category
        else:
            flash('Failed to add category.', 'danger')

    return render_template('add_category.html',form=form)  # Render the form for adding a category (add_category.html)



@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    response = requests.get(f'http://localhost:5000/api/categories/{category_id}')
    category = response.json()
    #category = Category.query.get_or_404(category_id)
    form = CategoryForm()
    if form.validate_on_submit():
            name = form.name.data.strip()  # Remove leading/trailing whitespaces
            image_file = form.image.data
            unique_filename = None  # Initialize with None
            if image_file:
                    
                random_hex = secrets.token_hex(8)
                _, file_extension = os.path.splitext(image_file.filename)
                unique_filename = random_hex + file_extension
            
                files = {'image': (unique_filename, image_file.read())}  # Use the image file object directly
            else:
                files=None
            data = {'name': name}
            response = requests.put(f'http://localhost:5000/api/categories/{category.id}', data=data, files=files)

            if response.status_code == 200:
                flash('Category updated successfully', 'success')
                return redirect(url_for('admin_categories'))
            else:
                error_message = response.json().get('message')
                flash(error_message, 'danger')
                flash('Failed to update category', 'danger')

    form.name.data = category['name']
    return render_template('edit_category.html', form=form, category=category)
    





@app.route('/admin/category/delete/<int:category_id>', methods=['GET'])
@login_required
def confirm_category_deletion(category_id):
    #category = Category.query.get_or_404(category_id)
    response = requests.get(f'http://localhost:5000/api/categories/{category_id}')
    category = response.json()
    return render_template('confirm_category_deletion.html', category=category)



@app.route('/admin/category/delete/<int:category_id>/execute', methods=['POST'])
@login_required
def delete_category_execution(category_id):
    response = requests.get(f'http://localhost:5000/api/categories/{category_id}')
    category = response.json()
    delete_response = requests.delete(f'http://localhost:5000/api/categories/{category_id}')
    if delete_response.status_code == 204:
        flash('Category deleted successfully.', 'success')
        return redirect(url_for('admin_categories'))
    else:
        flash('Failed to delete category.', 'danger')
        return render_template('confirm_category_deletion.html', category=category)
    


@app.route('/admin/categories/<int:category_id>/products')
@login_required
def category_products(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Fetch products related to the category
    products = Product.query.filter_by(category_id=category_id).all()

    return render_template('category_products.html', category=category, products=products,os=os)
    


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    
    # Fetch categories using the API
    categories_response = requests.get('http://localhost:5000/api/categories')
    
    # Check if the API request was successful
    if categories_response.status_code == 200:
        categories = categories_response.json()
        form.category_id.choices = [(category['id'], category['name']) for category in categories]
    else:
        flash('Failed to fetch categories from the API.', 'danger')
        categories = []
    
    if form.validate_on_submit():
        name = form.name.data.strip()  # Remove leading/trailing whitespaces
        manufacture_date = form.manufacture_date.data
        expiry_date = form.expiry_date.data
        rate_per_unit = form.rate_per_unit.data
        stock_quantity = form.stock_quantity.data
        category_id = form.category_id.data
        image_file = form.image.data
        data = {
            'name': name,
            'manufacture_date': manufacture_date.strftime('%Y-%m-%d'),
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'rate_per_unit': rate_per_unit,
            'stock_quantity': stock_quantity,
            'category_id': category_id
        }
        files = {'image': image_file}
        name_lower = name.lower()

        # Check if a product with the same name (case-insensitive) already exists
        existing_product = Product.query.filter(func.lower(Product.name) == name_lower).first()

        if existing_product:
            flash('Product with the same name already exists', 'danger')
        else:
            response = requests.post('http://localhost:5000/api/products', data=data, files=files)
            if response.status_code == 201:
                flash('Product added successfully.', 'success')
                return redirect(url_for('admin_products'))  # Redirect to the products list page after adding a product
            else:
                flash('Failed to add product.', 'danger')
    
    return render_template('add_product.html', form=form, categories=categories)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    response = requests.get(f'http://localhost:5000/api/products/{product_id}')
    product = response.json()
    categories_response = requests.get('http://localhost:5000/api/categories')
    form = ProductForm(obj=product)
    # Check if the API request was successful
    if categories_response.status_code == 200:
        categories = categories_response.json()
        form.category_id.choices = [(category['id'], category['name']) for category in categories]
    else:
        flash('Failed to fetch categories from the API.', 'danger')
        categories = []

    
    if form.validate_on_submit():
        name = form.name.data.strip()  # Remove leading/trailing whitespaces
        manufacture_date = form.manufacture_date.data
        expiry_date = form.expiry_date.data
        rate_per_unit = form.rate_per_unit.data
        stock_quantity = form.stock_quantity.data
        category_id = form.category_id.data
        image_file = form.image.data
        data = {
            'name': name,
            'manufacture_date': manufacture_date.strftime('%Y-%m-%d'),
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'rate_per_unit': rate_per_unit,
            'stock_quantity': stock_quantity,
            'category_id': category_id
        }
        files = {'image': image_file}
        response = requests.put(f'http://localhost:5000/api/products/{product["id"]}', data=data, files=files)
        if response.status_code == 201:
            flash('Product added successfully.', 'success')
            return redirect(url_for('admin_products'))  # Redirect to the products list page after adding a product
        else:
            flash('Failed to edit product.', 'danger')
            
    return render_template('edit_product.html', form=form,  product=product, categories=categories,os=os)


@app.route('/admin/product/delete/<int:product_id>', methods=['GET'])
@login_required
def confirm_product_deletion(product_id):
    return None

@app.route('/admin/product/delete/<int:product_id>/execute', methods=['POST'])
@login_required
def delete_product(product_id):
    return None

@app.route('/admin/add_quantity/<int:product_id>', methods=['POST'])
@login_required
def add_quantity(product_id):
    return None
'''

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    categories = Category.query.all()
    products = Product.query.all()
    if current_user.role.name == 'Admin':
        # Implement admin dashboard logic here
        return render_template('admin_dashboard.html',categories=categories,products=products)
    else:
        
        return redirect(url_for('user_login'))
    
@app.route('/admin_dashboard/search', methods=['POST'])
@login_required
def admin_dashboard_search():
    categories1 = Category.query.all()
    products1 = Product.query.all()
    search_type = request.form.get('search_type')
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

        elif search_type == 'manufacture_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products = Product.query.filter(Product.manufacture_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date After.', 'danger')
        elif search_type == 'manufacture_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.manufacture_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date Before.', 'danger')
        elif search_type == 'expiry_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date After.', 'danger')
        elif search_type == 'expiry_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date Before.', 'danger')
        elif search_type == 'price_above':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit > search_price).all()
            except ValueError:
                flash('Invalid price format for Price Above.', 'danger')
        elif search_type == 'price_below':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit < search_price).all()
            except ValueError:
                flash('Invalid price format for Price Below.', 'danger')

    return render_template('admin_dashboard_search.html', categories=categories, products=products, categories1=categories1, products1=products1, os=os)

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = Category.query.all()
    
    return render_template('admin_categories.html', categories=categories,os=os)

'''
@app.route('/admin_category/search', methods=['POST'])
@login_required
def admin_category_search():
    categories1 = Category.query.all()
    products1 = Product.query.all()
    search_type = 'category'
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        

    return render_template('admin_category_search.html', categories=categories,categories1=categories1,products1=products1,os=os)'''

@app.route('/admin/products')
@login_required
def admin_products():
    categories = Category.query.all()
    products = Product.query.all()
    return render_template('admin_products.html',categories=categories, products=products,os=os)

'''@app.route('/admin_product/search', methods=['POST'])
@login_required
def admin_product_search():
    categories1 = Category.query.all()
    products1 = Product.query.all()
    search_type = 'product'
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

    return render_template('admin_product_search.html', categories=categories, products=products,categories1=categories1,products1=products1,os=os)'''


@app.route('/admin/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()

    if form.validate_on_submit():
        name = form.name.data.strip()  # Remove leading/trailing whitespaces
        image_file = form.image.data

        # Convert the input name to lowercase
        name_lower = name.lower()

        # Check if a category with the same name (case-insensitive) already exists
        existing_category = Category.query.filter(func.lower(Category.name) == name_lower).first()

        if existing_category:
            flash('Category with the same name already exists', 'danger')
        else:
            unique_filename = None  # Initialize with None

            if image_file:
                # Generate a unique filename
                random_hex = secrets.token_hex(8)
                _, file_extension = os.path.splitext(image_file.filename)
                unique_filename = random_hex + file_extension

                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)

            category = Category(name=name, image=unique_filename)
            db.session.add(category)

            try:
                db.session.commit()
                flash('Category added successfully', 'success')
                return redirect(url_for('admin_categories'))
            except IntegrityError:
                db.session.rollback()
                flash('Category with the same image file name already exists', 'danger')

    return render_template('add_category.html', form=form)

@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)  # Populate the form with existing category data
    
    if form.validate_on_submit():
        # Check if the new category name conflicts with existing categories
        new_name = form.name.data.strip().lower()
        existing_category = Category.query.filter(func.lower(Category.name) == new_name).first()

        if existing_category and existing_category.id != category_id:
            flash('Category with the same name already exists', 'danger')
        else:
            if not form.image.data:  # Check if an image was provided
                flash('An image is required for category updates', 'danger')
            else:
                if category.image:
                    image_path = category.image
                    image_filename = os.path.basename(image_path)
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                
                form.populate_obj(category)  # Update the category with form data
                image_filename = save_uploaded_file(form.image.data)  # Save the new image file
                category.image = image_filename  # Update the category's image field with the new filename

                db.session.commit()
                flash('Category updated successfully', 'success')
                return redirect(url_for('admin_categories'))
    
    return render_template('edit_category.html', form=form, category=category)


@app.route('/admin/category/delete/<int:category_id>', methods=['GET'])
@login_required
def confirm_category_deletion(category_id):
    category = Category.query.get_or_404(category_id)
    return render_template('confirm_category_deletion.html', category=category)

@app.route('/admin/category/delete/<int:category_id>/execute', methods=['POST'])
@login_required
def delete_category_execution(category_id):
        category = Category.query.get_or_404(category_id)
    
    
        image_path = category.image

        if os.path.exists(image_path):
            os.remove(image_path)
       

        try:
            image_filename = os.path.basename(image_path)
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        except Exception as e:
            flash(f'Error deleting image file: {str(e)}', 'danger')

        # Delete associated products and their images
        products = category.products
        for product in products:
            product_image_path = product.image
            if os.path.exists(product_image_path):
                os.remove(product_image_path)
            

            try:
                product_image_filename = os.path.basename(product_image_path)
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product_image_filename))
            except Exception as e:
                flash(f'Error deleting product image file for {product.name}: {str(e)}', 'danger')

        
        # Handle category deletion here
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully', 'success')
        return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/products')
@login_required
def category_products(category_id):
    # Fetch the category based on category_id
    category = Category.query.get_or_404(category_id)
    
    # Fetch products related to the category
    products = Product.query.filter_by(category_id=category_id).all()

    return render_template('category_products.html', category=category, products=products,os=os)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    categories = Category.query.all()
    form.category_id.choices = [(category.id, category.name) for category in categories]
    if form.validate_on_submit():
        name = form.name.data.strip()  # Remove leading/trailing whitespaces
        rate_per_unit = form.rate_per_unit.data
        stock_quantity = form.stock_quantity.data
        manufacture_date = form.manufacture_date.data
        expiry_date = form.expiry_date.data
        category_id = form.category_id.data
        image_file = form.image.data
        # Convert the input name to lowercase
        name_lower = name.lower()

        # Check if product with the same name (case-insensitive) already exists
        existing_product = Product.query.filter(func.lower(Product.name) == name_lower).first()

        if existing_product:
            flash('Product with the same name already exists', 'danger')
        else:
            unique_filename = None  # Initialize with None

            if image_file:
                # Generate a unique filename
                random_hex = secrets.token_hex(8)
                _, file_extension = os.path.splitext(image_file.filename)
                unique_filename = random_hex + file_extension

                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)

           
            product = Product(name=name, rate_per_unit=rate_per_unit,stock_quantity=stock_quantity, manufacture_date=manufacture_date,
                          expiry_date=expiry_date, image=unique_filename, category_id=category_id)
            db.session.add(product)

            try:
                db.session.commit()
                flash('Product added successfully', 'success')
                return redirect(url_for('admin_products'))
            except IntegrityError:
                db.session.rollback()
                flash('Product with the same image file name already exists', 'danger')

    return render_template('add_product.html', form=form,categories=categories)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    # Fetch the categories here and pass them to the template
    categories = Category.query.all()
    form.category_id.choices = [(category.id, category.name) for category in categories]  # Set the choices

    
    if form.validate_on_submit():
        # Check if the new category name conflicts with existing categories
        new_name = form.name.data.strip().lower()
        existing_product = Product.query.filter(func.lower(Product.name) == new_name).first()

        if existing_product and existing_product.id != product_id:
            flash('Product with the same name already exists', 'danger')
        else:
            if not form.image.data:  # Check if an image was provided
                flash('An image is required for product updates', 'danger')
            else:
                if product.image:
                    image_path = product.image
                    image_filename = os.path.basename(image_path)
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                form.populate_obj(product)  # Update the category with form data
                image_filename = save_uploaded_file(form.image.data)  # Save the new image file
                product.image = image_filename  # Update the category's image field with the new filename

                db.session.commit()
                flash('Product updated successfully', 'success')
                return redirect(url_for('admin_products'))
    
    return render_template('edit_product.html', form=form, product=product, categories=categories,os=os)




@app.route('/admin/product/delete/<int:product_id>', methods=['GET'])
@login_required
def confirm_product_deletion(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('confirm_product_deletion.html', product=product)

@app.route('/admin/product/delete/<int:product_id>/execute', methods=['POST'])
@login_required
def delete_product(product_id):
        product = Product.query.get_or_404(product_id)
    
    
        image_path = product.image

        if os.path.exists(image_path):
            os.remove(image_path)
       

        try:
            image_filename = os.path.basename(image_path)
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        except Exception as e:
            flash(f'Error deleting image file: {str(e)}', 'danger')
 
        
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully', 'success')
        return redirect(url_for('admin_products'))


@app.route('/admin/add_quantity/<int:product_id>', methods=['POST'])
@login_required
def add_quantity(product_id):
    # Get the product by ID
    product = Product.query.get(product_id)
    
    if product is None:
        # Handle the case where the product doesn't exist
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_products'))

    try:
        # Get the quantity from the form
        quantity = int(request.form['quantity'])
        if quantity < 0:
            flash('Quantity must be a positive number.', 'danger')
        else:
            # Update the Stock_quantity of the product
            product.stock_quantity += quantity
            db.session.commit()
            flash(f'Quantity added: {quantity}', 'success')
    except ValueError:
        flash('Invalid quantity input.', 'danger')
    
    return redirect(url_for('admin_products'))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.role.name == 'User':
        categories = Category.query.all()
        products = Product.query.all()
        user = current_user  # Assuming you're using Flask-Login
        return render_template('user_dashboard.html', categories= categories,products=products, user=user, os=os)
        
    else:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('admin_login'))
    
@app.route('/user_dashboard/search', methods=['POST'])
@login_required
def user_dashboard_search():
    categories1 = Category.query.all()
    products1 = Product.query.all()
    search_type = request.form.get('search_type')
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

        elif search_type == 'manufacture_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products = Product.query.filter(Product.manufacture_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date After.', 'danger')
        elif search_type == 'manufacture_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.manufacture_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date Before.', 'danger')
        elif search_type == 'expiry_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date After.', 'danger')
        elif search_type == 'expiry_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date Before.', 'danger')
        elif search_type == 'price_above':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit > search_price).all()
            except ValueError:
                flash('Invalid price format for Price Above.', 'danger')
        elif search_type == 'price_below':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit < search_price).all()
            except ValueError:
                flash('Invalid price format for Price Below.', 'danger')

    return render_template('user_dashboard_search.html', categories=categories, products=products,categories1=categories1,products1=products1,os=os)
    
@app.route('/user/categories/<int:category_id>/products')
@login_required
def user_category_products(category_id):
    # Fetch the category based on category_id
    category = Category.query.get_or_404(category_id)
    
    # Fetch products related to the category
    products = Product.query.filter_by(category_id=category_id).all()

    return render_template('user_category_products.html', category=category, products=products,os=os)

@app.route('/user/product_detail/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    return render_template('product_detail.html', categories= categories, product=product,os=os)




@app.route('/user/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    # Check if the product is already in the cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if product.stock_quantity >= 1:
        if cart_item:
            cart_item.quantity += 1
            product.stock_quantity -= 1
        else:
            cart_item = CartItem(cart_id=cart.id, product_id=product.id, category_id=product.category_id, quantity=1)
            product.stock_quantity -= 1
        
        db.session.add(cart_item)
        db.session.commit()
        flash('Product added to cart successfully', 'success')
    else:
        flash('Product quantity is insufficient to add to the cart', 'danger')

    return redirect(url_for('user_dashboard'))


@app.route('/user/remove_from_cart/<int:cart_item_id>')
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)

    # Check if the cart item belongs to the current user
    if cart_item.cart.user_id == current_user.id:
        product = cart_item.product
        product.stock_quantity += cart_item.quantity  # Increase stock_quantity
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from the cart', 'success')
    else:
        flash('You do not have permission to remove this item from the cart', 'danger')

    return redirect(url_for('view_cart'))


@app.route('/user/buy/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy(product_id):
    product = Product.query.get_or_404(product_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    # Check if the product is already in the cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if product.stock_quantity >= 1:
        if cart_item:
            cart_item.quantity += 1
            product.stock_quantity -= 1
        else:
            cart_item = CartItem(cart_id=cart.id, product_id=product.id, category_id=product.category_id, quantity=1)
            product.stock_quantity -= 1
        
        db.session.add(cart_item)
        db.session.commit()
        flash('Product added to cart successfully', 'success')
    else:
        flash('Product quantity is insufficient to add to the cart', 'danger')
    return redirect(url_for('view_cart'))

@app.route('/user/view_cart')
@login_required
def view_cart():
    # Fetch the user's cart and cart items
    user_cart = Cart.query.filter_by(user_id=current_user.id).first()
    cart_items = user_cart.items if user_cart else []

    # Create a list to store cart items with product details
    cart_items_with_product = []

    # Calculate the total amount for each cart item and store it
    total_amount = 0

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        item_total = product.rate_per_unit * cart_item.quantity
        total_amount += item_total

        cart_items_with_product.append({
            "cart_item": cart_item,
            "product": product,
            "item_total": item_total
        })

    return render_template('view_cart.html', cart_items=cart_items_with_product, total_amount=total_amount)

@app.route('/user/add_quantity_to_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def add_quantity_to_cart(cart_item_id):
    # Fetch the cart item
    cart_item = CartItem.query.get_or_404(cart_item_id)
    product = cart_item.product
    if product.stock_quantity >= 1:
        product.stock_quantity -= 1
        # Increment the quantity
        cart_item.quantity += 1
        db.session.commit()
    else:
        flash("insaficient Product in shop ",'danger')
    # Redirect back to the cart page
    return redirect(url_for('view_cart'))


@app.route('/user/remove_quantity_to_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_quantity_to_cart(cart_item_id):
    # Fetch the cart item
    cart_item = CartItem.query.get_or_404(cart_item_id)
    product = cart_item.product
    if cart_item.quantity >= 1:
        product.stock_quantity += 1
        # Increment the quantity
        cart_item.quantity -= 1
        db.session.commit()
    else:
        flash("insaficient Cart item ",'danger')
    # Redirect back to the cart page
    return redirect(url_for('view_cart'))




@app.route('/user/checkout')
@login_required
def checkout():
    # Assuming you have a cart for the current user
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        flash('Your cart is empty. Add items to your cart before checkout.', 'danger')
        return redirect(url_for('view_cart'))

    # Calculate the total amount of the items in the cart
    total_amount = 0
    items_to_remove = []
    checkout_date = datetime.now()

    for cart_item in cart.items:
        product = cart_item.product
        total_amount += product.rate_per_unit * cart_item.quantity
        items_to_remove.append(cart_item)
        shopping_list_item = ShoppingList(
            user_id=current_user.id,
            product_id=product.id,
            category_id=product.category_id,
            quantity=cart_item.quantity,
            product_name=product.name,
            product_rate_per_unit=product.rate_per_unit,
            category_name=product.category_ref.name,  
            checkout_date=checkout_date
        )
        db.session.add(shopping_list_item)
    db.session.commit()
    # Remove checked-out products from the cart
    for cart_item in items_to_remove:
        cart.items.remove(cart_item)
        db.session.delete(cart_item)

    db.session.commit()

    return render_template('checkout_summary.html', total_amount=total_amount)

@app.route('/user/shopping_history')
@login_required  
def shopping_history():
    shopping_history = ShoppingList.query.filter_by(user_id=current_user.id).all()
    shopping_totals = defaultdict(float)

    # Group shopping history entries by checkout date and calculate total amounts
    for item in shopping_history:
        checkout_date = item.checkout_date.strftime('%Y-%m-%d')  # Format date as a string
        total_amount = item.quantity * item.product_rate_per_unit
        shopping_totals[checkout_date] += total_amount

    return render_template('shopping_history.html', shopping_history=shopping_history,shopping_totals=shopping_totals)


@app.route('/user/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        password = request.form.get('password')
        
        # Check if the provided password matches the user's current password
        if current_user.check_password(password):
            # Get the user's cart
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            
            if cart:
                # Get cart items associated with this cart
                cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
                
                # Restore product quantities
                for cart_item in cart_items:
                    product = cart_item.product
                    product.stock_quantity += cart_item.quantity
                
                # Delete the cart items
                CartItem.query.filter_by(cart_id=cart.id).delete()
                
                # Delete the cart itself
                db.session.delete(cart)
            
            # Delete the user's account
            db.session.delete(current_user)
            db.session.commit()
            
            flash('Your account has been deleted successfully', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
    
    return render_template('confirm_delete_account.html')


@app.route('/user_dashboard/search_home', methods=['POST'])
def user_dashboard_search_home():
    categories1 = Category.query.all()
    products1 = Product.query.all()
    search_type = request.form.get('search_type')
    search_query = request.form.get('search_query')
    
    categories = []
    products = []

    if search_type and search_query:
        if search_type == 'category':
            categories = Category.query.filter(Category.name.ilike(f'%{search_query}%')).all()
        elif search_type == 'product':
            products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()

        elif search_type == 'manufacture_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products = Product.query.filter(Product.manufacture_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date After.', 'danger')
        elif search_type == 'manufacture_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.manufacture_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Manufacture Date Before.', 'danger')
        elif search_type == 'expiry_date_after':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date >= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date After.', 'danger')
        elif search_type == 'expiry_date_before':
            try:
                search_date = datetime.strptime(search_query, '%Y-%m-%d')
                products  = Product.query.filter(Product.expiry_date <= search_date).all()
            except ValueError:
                flash('Invalid date format for Expiry Date Before.', 'danger')
        elif search_type == 'price_above':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit > search_price).all()
            except ValueError:
                flash('Invalid price format for Price Above.', 'danger')
        elif search_type == 'price_below':
            try:
                search_price = float(search_query)
                products  = Product.query.filter(Product.rate_per_unit < search_price).all()
            except ValueError:
                flash('Invalid price format for Price Below.', 'danger')
    print(categories)
    return render_template('user_dashboard_search_home.html', categories=categories, products=products,categories1=categories1,products1=products1,os=os)

@app.errorhandler(401)
def unauthorized_error(error):
    flash('You must log in to access this page.', 'danger')
    return redirect(url_for('user_login'))
@app.route('/')
def homepage():
    categories = Category.query.all()
    products = Product.query.all()

   
    current_year = datetime.now().year  
    today = datetime.now().date()
    return render_template('homepage.html', current_year=current_year,categories=categories,products=products,os=os)

if __name__ == '__main__':
    app.run(debug=True)