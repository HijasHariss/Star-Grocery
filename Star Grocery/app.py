from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin, Security, SQLAlchemyUserDatastore, roles_required, http_auth_required, login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from PIL import Image
import os

app=Flask(__name__)
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db_path= os.path.join(os.path.dirname(__file__), 'data', 'Data.sqlite3')
app.config['SECRET_KEY']='STARGROCERY'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
from models import *
db.init_app(app)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

app.jinja_env.globals['get_flashed_messages'] = get_flashed_messages


@app.route('/', methods=['GET', 'POST'])
def Login():
    if request.method == 'POST':
       username = request.form['username']
       password = request.form['password']
       
       user=User.query.filter_by(username=username, password=password).first()

       if user:
           session['userId'] = user.id
           session['username']=username
           session['usertype'] = user.usertype
           if user.usertype=='admin':
               return redirect(url_for('AdminDashboard'))
           elif user.usertype=='customer':
               return redirect(url_for('StarGrocery'))

       flash("Invalid Username or Password", "danger")
    return render_template('Login.html')  

@app.route('/Register')
def Register():
    return render_template('Register.html')
@app.route('/Register', methods=['POST'])
def Register_user():
    if request.method=='POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

    if not username or not email or not password:
        flash('All fields are required', 'danger')
        return redirect(url_for('Register'))

    if user_datastore.get_user(username):
        flash('Username already taken. Please choose another.', 'danger')
        return redirect(url_for('Register'))
    
    if user_datastore.get_user(email):
        flash('You already have an account. Please login.', 'danger')
        return redirect(url_for('Login'))    

    user = user_datastore.create_user(username=username, email=email, password=password, usertype='customer', role_id=2)
    user_datastore.add_role_to_user(user, 'customer')

    db.session.commit()

    flash('Registration successful. You can now log in.', 'success')
    return redirect(url_for('Login'))


def is_authenticated():
    return 'username' in session


@app.route('/Logout')
def Logout():
    session.pop('username', None)
    session.pop('userId', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('Login'))


@app.route('/AdminDashboard')
def AdminDashboard():
    usertype = session.get("usertype")
    if usertype != 'admin':
        flash("Only Admins allowed.", 'danger')
        return redirect(url_for('Login'))
    return render_template('AdminDashboard.html') 


@app.route('/AddProduct', methods=['GET', 'POST'])
def addproduct():
    usertype = session.get('usertype')
    if usertype != 'admin':
        flash("Only Admins allowed.", 'danger')
        return redirect(url_for('Login'))

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = float(request.form['stock'])
        offer = request.form['offer']
        category = request.form['category']
        uimage = request.files['image']

        existing = Product.query.filter_by(name=name).first()
        if existing:
            flash(f"A product with the same name '{ name }' already exists.", 'danger')
            return redirect(url_for('addproduct'))

        if not offer:
            offer = None

        if uimage:
            filename = secure_filename(uimage.filename)
            image = os.path.join(app.config['UPLOAD_FOLDER'], ("pictures/" + filename))
            uimage.save(image)

            resized = Image.open(image)
            resized.thumbnail((200, 200))
            resized.save(image)
            image = image.replace("static", "")
            image = image.replace("\\", "")
        else:
            image = 'pictures/Default.jpg'

        product = Product(name=name, price=price, stock=stock, offer=offer, category=category, image=image)
        db.session.add(product)
        db.session.commit()

        flash('Product added successfully', 'success')
        return redirect(url_for('addproduct'))

    return render_template('Add Product.html')    


@app.route('/EditProduct', methods=['GET', 'POST'])
def editproduct():
    usertype = session.get('usertype')
    if usertype != 'admin':
        flash("Only Admins allowed.", 'danger')
        return redirect(url_for('Login'))

    if request.method == 'POST':
        name = request.form['name']
        new_name = request.form['new_name']
        new_price = request.form.get('new_price')
        new_stock = request.form.get('new_stock')
        new_offer = request.form.get('new_offer')

        existing = Product.query.filter_by(name=name).first()
        if existing:
            if new_name:
                existing.name = new_name
            if new_price:
                existing.price = float(new_price)
            if new_stock:
                existing.stock = float(new_stock)
            if new_offer:
                existing.offer = int(new_offer)
            db.session.commit()
            flash('Product updated successfully!', 'success')
        else:
            flash('Product not found', 'danger')
        
        return redirect(url_for('editproduct'))

    products = Product.query.all()
    return render_template('Edit Product.html', products=products)

@app.route('/DeleteProduct', methods=['GET', 'POST'])
def deleteproduct():
    usertype = session.get('usertype')
    if usertype != 'admin':
        flash("Only Admins allowed.", 'danger')
        return redirect(url_for('Login'))
    
    if request.method == 'POST':
        name = request.form['name']

        product = Product.query.filter_by(name=name).first()

        if product:
            return render_template('Delete Confirmation.html', product=product)
        else:
            flash('Product not found', 'danger')

    products = Product.query.all()
    return render_template('Delete Product.html', products=products)

@app.route('/ConfirmDelete/<int:id>', methods=['POST'])
def confirmdelete(id):
    product = Product.query.get(id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully', 'success')
        return redirect(url_for('deleteproduct'))
    else:
        flash('Product not found', 'danger')
        return redirect(url_for('deleteproduct'))


@app.route('/Store')

def StarGrocery():
    snacks = Product.query.filter_by(category='Snacks').all()
    grains = Product.query.filter_by(category='Grains & Cereals').all()
    spoffer = Product.query.filter(Product.offer.isnot(None)).all()
    fruitsveg = Product.query.filter_by(category='Fruits & Vegetables').all()
    if is_authenticated():
        return render_template('Star Grocery.html', fruitsveg=fruitsveg, spoffer=spoffer, grains=grains, snacks=snacks)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

@app.route('/Search', methods=['GET'])

def Search():
    query = request.args.get('query')
    if query:
        products = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
    else:
        products = []

    return render_template('Search Result.html', products=products)


@app.route('/SpecialOffer')

def SpecialOffers():
    spoffer = Product.query.filter(Product.offer.isnot(None)).all()    

    if is_authenticated():
        return render_template('Special Offers.html', products=spoffer)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))


@app.route('/Fruits&Vegetables')

def FruitsVegetables():
    fruitsveg = Product.query.filter_by(category='Fruits & Vegetables').all()
    
    if is_authenticated():
        return render_template('Fruits & Vegetables.html', products=fruitsveg)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

@app.route('/DairyProducts')

def DairyProducts():
    dairy = Product.query.filter_by(category='Dairy Products').all()

    if is_authenticated():
        return render_template('Dairy Products.html', products=dairy)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

@app.route('/Grains&Cereals')

def GrainsCereals():
    grains = Product.query.filter_by(category='Grains & Cereals').all()

    if is_authenticated():
        return render_template('Grains & Cereals.html', products=grains)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

#Snacks Route
@app.route('/Snacks')

def Snacks():
    snacks = Product.query.filter_by(category='Snacks').all()

    if is_authenticated():
        return render_template('Snacks.html', products=snacks)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

#Beverages Route
@app.route('/Beverages')

def Beverages():
    bever = Product.query.filter_by(category='Beverages').all()

    if is_authenticated():
        return render_template('Beverages.html', products=bever)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

#EggMF Route
@app.route('/Egg,Meat&Fish')

def EggMeatFish():
    egg = Product.query.filter_by(category='Egg, Meat & Fish').all()

    if is_authenticated():
        return render_template('Egg, Meat & Fish.html', products=egg)
    else:
        flash('Please log in to access the page.', 'warning')
        return redirect(url_for('Login'))

#Product Purchase Route
@app.route('/Product/<int:id>')
def ProductDisplay(id):
    product = Product.query.get(id)
    return render_template('Product Display.html', product=product)

@app.route('/Add Cart/<int:id>', methods=['POST'])

def AddCart(id):
    product = Product.query.get(id)
    userId = session.get('userId')

    if userId:
        quantity = int(request.form['Quantity'])
        if quantity > 0 and quantity <= product.stock:
            cartItem = Cart(userId=userId, productId=product.id, quantity=quantity, name=product.name, category=product.category)
            db.session.add(cartItem)
            db.session.commit()
            flash(f'{quantity} {product.name}(s) added to cart!', 'success')
        else:
            flash('Invalid quantity or stock exceeded.', 'danger')
    else:
        flash('Please log in to add items to the cart.', 'warning')
        return redirect(url_for('Login'))
    
    return redirect(url_for('MyCart', id=product.id))

@app.route('/Remove', methods=['POST'])

def RemoveCart():
    userId = session.get('userId')
    productId = request.form.get('productId')

    cartItem = Cart.query.filter_by(userId=userId, productId=productId).first()
    if cartItem: 
       db.session.delete(cartItem) 
       db.session.commit() 
       flash('Product removed from cart.', 'success') 
    else: 
       flash('Product not found in cart.', 'danger')
 
    return redirect(url_for('MyCart'))

@app.route('/MyCart')

def MyCart():
    userId = session.get('userId')
    cartItems = Cart.query.filter_by(userId=userId).all()
    TotalPrice=0
    for item in cartItems:
        product = Product.query.get(item.productId)
        item.name = product.name
        if product.offer:
            item.price=product.price-(product.price*product.offer/100)
        else:
            item.price = product.price
        item.total = item.price * item.quantity
        TotalPrice += item.total
    return render_template('MyCart.html', cartItems=cartItems, TotalPrice=TotalPrice)

@app.route('/ProceedtoPayment', methods=['POST'])
def ProceedToPayment():
    userId = session.get('userId')
    cartItems = Cart.query.filter_by(userId=userId).all()

    for cartItem in cartItems:
        exist=Sold.query.filter_by(pid=cartItem.productId).first()
        if exist:
             exist.quantity += cartItem.quantity
        else:
             soldItem = Sold(
                  pid = cartItem.productId,
                  category = cartItem.category,
                  name = cartItem.name,
                  quantity = cartItem.quantity
             )
             db.session.add(soldItem)

        products = Product.query.get(cartItem.productId)
        products.stock -= cartItem.quantity
        db.session.commit()

    Cart.query.filter_by(userId=userId).delete()
    db.session.commit()

    flash('Payment successful! Thank you for your purchase.', 'success')
    return redirect(url_for('StarGrocery'))

#About Route
@app.route('/About')
def About():
    return render_template('About.html')

#Contact Route
@app.route('/Contact')
def Contact():
    return render_template('Contact.html')
           
if __name__=="__main__":
    app.run(debug=True)

    