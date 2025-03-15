from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import os
from datetime import date, timedelta, datetime
from werkzeug.utils import secure_filename
import json
from sqlalchemy.orm import Session
import pprint

KASSAL_API_KEY = os.getenv("KASSAL_API_KEY", "RSoYsw9xCYwH5pPWh3zsWYSw50gi9nLM79MIz1xv")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = 'your_secret_key'

# *Oppdatert PostgreSQL database URI*
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Eirik2006@localhost:5432/Kaloriteller")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    setup_complete = db.Column(db.Boolean, default=False)
    
    # Nytt felt for å kunne identifisere admin-brukere
    is_admin = db.Column(db.Boolean, default=False)

    favorites = db.relationship('UserFavorite', back_populates='user')
    goal = db.relationship('UserGoal', backref='user', uselist=False)
    weights = db.relationship('WeightLog', backref='user', lazy=True)



class UserGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    activity_level = db.Column(db.String(50), nullable=True)
    goal_type = db.Column(db.String(50), nullable=True)
    calorie_goal = db.Column(db.Float, nullable=True)
    protein_goal = db.Column(db.Float, nullable=True)
    fat_goal = db.Column(db.Float, nullable=True)
    carb_goal = db.Column(db.Float, nullable=True)


class DayLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    entries = db.relationship('LogEntry', backref='day', lazy=True)


class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('day_log.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    proteins = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)


class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    proteins = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=True)  # Lagrer bildestien
    created_by_user = db.Column(db.Boolean, default=True)
    approved = db.Column(db.Boolean, default=False)   # <--- NYTT FELT
    popularity = db.Column(db.Integer, default=0)

    favorited_by = db.relationship('UserFavorite', back_populates='product')

    def get_image_url(self):
        """ Returnerer riktig bilde-URL """
        if self.image and self.image.startswith("http"):  # Eksternt bilde
            return self.image
        elif self.image:  # Lokalt bilde
            return url_for('static', filename=f"uploads/{self.image}")
        return url_for('static', filename="uploads/default_image.png")  # Standardbilde


class UserFavorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    user = db.relationship('User', back_populates='favorites')
    product = db.relationship('Product', back_populates='favorited_by')


class UserLoggedProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    times_selected = db.Column(db.Integer, default=1)
    last_selected = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="logged_products")
    product = db.relationship("Product", backref="logged_by_users")


class SelectedProduct(db.Model):
    __tablename__ = 'selected_products'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # ForeignKey til Product
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product = db.relationship('Product')  # lar oss gjøre sp.product.weight

    product_name = db.Column(db.String(255), nullable=False)
    calories_per_100g = db.Column(db.Float, nullable=True)
    proteins_per_100g = db.Column(db.Float, nullable=True)
    fat_per_100g = db.Column(db.Float, nullable=True)
    carbohydrates_per_100g = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    times_selected = db.Column(db.Integer, default=1)
    last_selected = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='selected_products')

    def __repr__(self):
        return f"<SelectedProduct {self.product_name} (User {self.user_id})>"


# Login loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passordene stemmer ikke overens!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('E-post allerede registrert!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Brukernavnet er allerede tatt!', 'danger')
            return redirect(url_for('register'))

        new_user = User(email=email, username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Konto opprettet! Logg inn.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if not user or user.password != password:
            flash('Invalid credentials!', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('Welcome back!', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))


@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if not current_user.setup_complete:
        return redirect(url_for('setup_user'))

    # Hent valgt dato fra query-parameter eller sesjon, ellers bruk dagens dato
    date_param = request.args.get('date', None)
    if date_param:
        selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        session['selected_date'] = selected_date.isoformat()
    else:
        selected_date_str = session.get('selected_date', date.today().isoformat())
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    # Finn eller opprett DayLog
    day_log = DayLog.query.filter_by(date=selected_date, user_id=current_user.id).first()
    if not day_log:
        day_log = DayLog(date=selected_date, user_id=current_user.id)
        db.session.add(day_log)
        db.session.commit()

    # Beregn daglige totaler
    daily_totals = {
        'calories': sum(e.calories for e in day_log.entries),
        'proteins': sum(e.proteins for e in day_log.entries),
        'fat': sum(e.fat for e in day_log.entries),
        'carbohydrates': sum(e.carbohydrates for e in day_log.entries),
    }

    # Hent favorittprodukter
    favorite_products = (
        db.session.query(Product)
        .join(UserFavorite, UserFavorite.product_id == Product.id)
        .filter(UserFavorite.user_id == current_user.id)
        .all()
    )

    # Hent brukerens mål
    user_goal = UserGoal.query.filter_by(user_id=current_user.id).first()

    # Beregn fremdrift for hver kategori
    goal_progress = {}
    if user_goal:
        for key, value in daily_totals.items():
            goal_key = key if key != 'calories' else 'calorie_goal'
            goal_value = getattr(user_goal, goal_key, 0)
            goal_progress[key] = round((value / goal_value) * 100, 1) if goal_value > 0 else 0

    goal_type_display = user_goal.goal_type if user_goal and user_goal.goal_type else "Ingen mål valgt"

    # -- METODE 1: Hardkode norske ukedager --
    # Mandag=0, Tirsdag=1, ... Søndag=6
    norwegian_days = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
    weekday_index = selected_date.weekday()  # Mandag=0, Søndag=6
    weekday_name = norwegian_days[weekday_index]

    return render_template(
        'index.html',
        daily_totals=daily_totals,
        daily_entries=day_log.entries,
        favorite_products=favorite_products,
        selected_date=selected_date,
        user_goal=user_goal,
        goal_progress=goal_progress,
        goal_type_display=goal_type_display,
        timedelta=timedelta,
        weekday_name=weekday_name
    )

@app.route('/log_weight', methods=['POST'])
@login_required
def log_weight():
    weight = float(request.form.get('weight'))
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

    # Sjekk om vekten allerede er loggført for denne datoen
    existing_entry = WeightLog.query.filter_by(user_id=current_user.id, date=date).first()
    if existing_entry:
        existing_entry.weight = weight  # Oppdater eksisterende vekt
    else:
        # Opprett ny logg for kroppsvekt
        new_weight = WeightLog(user_id=current_user.id, date=date, weight=weight)
        db.session.add(new_weight)

    db.session.commit()
    flash("Kroppsvekt loggført!", "success")
    return redirect(url_for('set_goal'))


@app.route('/set_goal', methods=['GET', 'POST'])
@login_required
def set_goal():
    # Hent eller opprett brukerens mål
    user_goal = UserGoal.query.filter_by(user_id=current_user.id).first()
    if not user_goal:
        user_goal = UserGoal(user_id=current_user.id)
        db.session.add(user_goal)
        db.session.commit()

    if request.method == 'POST':
        # Sjekk om brukeren sender inn kalorimål-skjema
        if 'calorie_goal' in request.form:
            calorie_goal = request.form.get('calorie_goal', '').strip()
            protein_goal = request.form.get('protein_goal', '').strip()
            fat_goal = request.form.get('fat_goal', '').strip()
            carb_goal = request.form.get('carb_goal', '').strip()
            # "goal_type" kan nå være "Kaloriunderskudd", "Kalorioverskudd" eller "Vedlikehold"
            goal_type = request.form.get('goal_type', '').strip()

            # Konverter til float hvis mulig
            calorie_goal = float(calorie_goal) if calorie_goal else None
            protein_goal = float(protein_goal) if protein_goal else None
            fat_goal = float(fat_goal) if fat_goal else None
            carb_goal = float(carb_goal) if carb_goal else None

            try:
                # Hvis ett av feltene er None, beregn det
                if calorie_goal is None:
                    calorie_goal = (protein_goal * 4) + (fat_goal * 9) + (carb_goal * 4)
                elif protein_goal is None:
                    protein_goal = (calorie_goal - (fat_goal * 9) - (carb_goal * 4)) / 4
                elif fat_goal is None:
                    fat_goal = (calorie_goal - (protein_goal * 4) - (carb_goal * 4)) / 9
                elif carb_goal is None:
                    carb_goal = (calorie_goal - (protein_goal * 4) - (fat_goal * 9)) / 4

                # Valider
                if any(val < 0 for val in [protein_goal, fat_goal, carb_goal]):
                    raise ValueError("Verdiene du oppga resulterer i negative makronæringsstoffer.")
                if (protein_goal * 4) + (fat_goal * 9) + (carb_goal * 4) > calorie_goal:
                    raise ValueError("Makronæringsstoffene overskrider kalorimålet.")

                # Oppdater UserGoal
                user_goal.calorie_goal = round(calorie_goal, 1)
                user_goal.protein_goal = round(protein_goal, 1)
                user_goal.fat_goal = round(fat_goal, 1)
                user_goal.carb_goal = round(carb_goal, 1)
                # Oppdater til "Kaloriunderskudd", "Kalorioverskudd" eller "Vedlikehold"
                user_goal.goal_type = goal_type

                db.session.commit()
                flash("Målene dine er oppdatert!", "success")
                return redirect(url_for('index'))

            except ValueError as e:
                flash(str(e), "danger")
                return redirect(url_for('set_goal'))

        # Sjekk om brukeren sender inn kroppsvekt-skjema
        elif 'weight' in request.form:
            weight = float(request.form.get('weight'))
            date_str = request.form.get('date')
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            existing_entry = WeightLog.query.filter_by(user_id=current_user.id, date=date_obj).first()
            if existing_entry:
                existing_entry.weight = weight
            else:
                new_weight = WeightLog(user_id=current_user.id, date=date_obj, weight=weight)
                db.session.add(new_weight)

            db.session.commit()
            flash("Kroppsvekt loggført!", "success")
            return redirect(url_for('set_goal'))

    # Hent vektdata for graf
    weight_logs = WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.date).all()
    weight_data = [{"date": w.date.isoformat(), "weight": w.weight} for w in weight_logs]

    return render_template('set_goal.html', goal=user_goal, weight_data=weight_data)


# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Beregningsfunksjoner for popupen
def calculate_bmr(gender, weight, height, age):
    if gender.lower() == 'mann':
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161

def calculate_tdee(bmr, activity_level):
    multipliers = {
        'Lite aktiv': 1.375,
        'Moderat aktiv': 1.55,
        'Veldig aktiv': 1.725
    }
    return bmr * multipliers.get(activity_level, 1.2)

def adjust_for_goal(tdee, weight, goal_type):
    if goal_type.lower() == 'cutting':
        daily_calories = tdee - 500
    elif goal_type.lower() == 'bulking':
        daily_calories = tdee + 500
    else:
        daily_calories = tdee

    protein = weight * 2
    fat = weight * 0.8
    carbs = (daily_calories - (protein * 4 + fat * 9)) / 4

    return daily_calories, protein, fat, carbs

# Rute for førstegangsoppsett-popup
@app.route('/setup_user', methods=['GET', 'POST'])
@login_required
def setup_user():
    if request.method == 'POST':
        data = request.json
        gender = data['gender']
        age = data['age']
        height = data['height']
        weight = data['weight']
        activity_level = data['activity_level']
        # Her forutsetter vi at `goal_type` kan være
        # "Kaloriunderskudd", "Kalorioverskudd" eller "Vedlikehold"
        goal_type = data['goal_type']

        bmr = calculate_bmr(gender, weight, height, age)
        tdee = calculate_tdee(bmr, activity_level)
        calories, protein, fat, carbs = adjust_for_goal(tdee, weight, goal_type)

        # Opprett et UserGoal-objekt med de nye terminologiene
        user_goal = UserGoal(
            user_id=current_user.id,
            gender=gender,
            age=age,
            height=height,
            weight=weight,
            activity_level=activity_level,
            goal_type=goal_type,      # "Kalorioverskudd"/"Kaloriunderskudd"/"Vedlikehold"
            calorie_goal=calories,
            protein_goal=protein,
            fat_goal=fat,
            carb_goal=carbs
        )

        db.session.add(user_goal)
        current_user.setup_complete = True
        db.session.commit()

        return jsonify({"success": True})

    return render_template('setup_popup.html')


@app.route('/add_favorite_from_log/<int:entry_id>', methods=['POST'])
@login_required
def add_favorite_from_log(entry_id):
    entry = LogEntry.query.get_or_404(entry_id)

    # Sjekk om produktet allerede finnes i `Product`
    product = Product.query.filter_by(name=entry.name, weight=entry.weight).first()

    if not product:
        # Opprett produktet hvis det ikke finnes
        product = Product(
            name=entry.name,
            weight=entry.weight,
            calories=entry.calories,
            proteins=entry.proteins,
            fat=entry.fat,
            carbohydrates=entry.carbohydrates
        )
        db.session.add(product)
        db.session.commit()  # Lagre produktet i databasen først

    # Sjekk om produktet allerede er favoritt for brukeren
    existing_favorite = UserFavorite.query.filter_by(user_id=current_user.id, product_id=product.id).first()

    if existing_favorite:
        flash(f"'{entry.name}' er allerede i dine favoritter!", "warning")
    else:
        # Opprett brukerbasert favoritt
        new_favorite = UserFavorite(user_id=current_user.id, product_id=product.id)
        db.session.add(new_favorite)
        db.session.commit()
        flash(f"'{entry.name}' ble lagt til favorittene dine!", "success")

    return redirect(url_for('index'))


@app.route('/toggle_favorite/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    product = Product.query.get_or_404(product_id)

    # Sjekk om produktet allerede er favorisert av den innloggede brukeren
    favorite = UserFavorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if favorite:
        # Fjern produktet fra favoritter
        db.session.delete(favorite)
        flash(f"'{product.name}' ble fjernet fra favorittene dine.", 'info')
    else:
        # Legg produktet til som favoritt
        new_favorite = UserFavorite(user_id=current_user.id, product_id=product_id)
        db.session.add(new_favorite)
        flash(f"'{product.name}' ble lagt til favorittene dine.", 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('index'))




@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form.get('search', '').strip()

    # 1) "Tidligere valgt" (SelectedProduct)
    selected_products = (
        db.session.query(SelectedProduct)
        .filter(
            SelectedProduct.user_id == current_user.id,
            SelectedProduct.product_name.ilike(f"%{query}%")
        )
        .order_by(SelectedProduct.times_selected.desc(), SelectedProduct.last_selected.desc())
        .all()
    )

    formatted_selected_products = []
    for sp in selected_products:
        # Forsøk å hente totalvekt fra sp.product (Product-tabellen) hvis product_id er satt
        if sp.product:
            total_weight = sp.product.weight  # f.eks. 540g
        else:
            total_weight = "Ukjent"

        formatted_selected_products.append({
            "id": sp.id,
            "name": sp.product_name,
            "calories_per_100g": sp.calories_per_100g or "Ukjent",
            "proteins_per_100g": sp.proteins_per_100g or "Ukjent",
            "fat_per_100g": sp.fat_per_100g or "Ukjent",
            "carbohydrates_per_100g": sp.carbohydrates_per_100g or "Ukjent",
            "weight": total_weight,
            "image_url": sp.image_url or url_for('static', filename="uploads/default_image.png"),
            "source": "Tidligere valgt",
            "priority": 0
        })

    # 2) Favorittprodukter – kun approved
    favorite_products = (
        db.session.query(Product)
        .join(UserFavorite, UserFavorite.product_id == Product.id)
        .filter(
            UserFavorite.user_id == current_user.id,
            Product.name.ilike(f"%{query}%"),
            Product.approved == True  # kun godkjente produkter
        )
        .all()
    )

    formatted_favorite_products = [
        {
            "id": product.id,
            "name": product.name,
            "calories_per_100g": (product.calories / product.weight) * 100
                if product.weight and product.calories else "Ukjent",
            "proteins_per_100g": (product.proteins / product.weight) * 100
                if product.weight and product.proteins else "Ukjent",
            "fat_per_100g": (product.fat / product.weight) * 100
                if product.weight and product.fat else "Ukjent",
            "carbohydrates_per_100g": (product.carbohydrates / product.weight) * 100
                if product.weight and product.carbohydrates else "Ukjent",
            "weight": product.weight if product.weight else "Ukjent",
            "image_url": product.get_image_url(),
            "source": "Favorittprodukt",
            "priority": 1
        }
        for product in favorite_products
    ]

    # 3) Populære produkter – kun approved
    popular_products = (
        db.session.query(Product)
        .filter(
            Product.name.ilike(f"%{query}%"),
            Product.approved == True
        )
        .order_by(Product.popularity.desc())
        .all()
    )

    formatted_popular_products = [
        {
            "id": product.id,
            "name": product.name,
            "calories_per_100g": (product.calories / product.weight) * 100
                if product.weight and product.calories else "Ukjent",
            "proteins_per_100g": (product.proteins / product.weight) * 100
                if product.weight and product.proteins else "Ukjent",
            "fat_per_100g": (product.fat / product.weight) * 100
                if product.weight and product.fat else "Ukjent",
            "carbohydrates_per_100g": (product.carbohydrates / product.weight) * 100
                if product.weight and product.carbohydrates else "Ukjent",
            "weight": product.weight if product.weight else "Ukjent",
            "image_url": product.get_image_url(),
            "source": "Populært produkt",
            "priority": 2
        }
        for product in popular_products
    ]

    # 4) Kassal (priority 3) og Open Food Facts (priority 4)
    kassal_products = fetch_kassal_products(query)
    for p in kassal_products:
        p["priority"] = 3

    off_products = fetch_open_food_facts_products(query)
    for p in off_products:
        p["priority"] = 4

    # Kombiner alle resultater
    combined_products = (
        formatted_selected_products +
        formatted_favorite_products +
        formatted_popular_products +
        kassal_products +
        off_products
    )

    print("\n🔍 **SØKERESULTATER (før duplikatfjerning og sortering):**")
    pprint.pprint(combined_products)

    # Fjern duplikater basert på prioritet (lav prioritet = “bedre”)
    unique_products = {}
    for prod in combined_products:
        name_key = prod["name"].lower()
        if name_key in unique_products:
            if prod["priority"] < unique_products[name_key]["priority"]:
                unique_products[name_key] = prod
        else:
            unique_products[name_key] = prod

    final_products = list(unique_products.values())

    # Sorter etter (priority, navn)
    final_products.sort(key=lambda x: (x["priority"], x["name"]))

    print("\n✅ **SØKERESULTATER (etter duplikatfjerning og sortering):**")
    pprint.pprint(final_products)

    return render_template('sok_resultat.html', produkter=final_products)



def fetch_open_food_facts_products(query, page_size=10):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "action": "process",
        "search_terms": query,
        "json": "true",
        "page_size": page_size,
        "countries_tags": "norway"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "id": None,
                "name": product.get("product_name", "Ukjent produkt"),
                "calories_per_100g": product.get("nutriments", {}).get("energy-kcal_100g", "Ukjent"),
                "proteins_per_100g": product.get("nutriments", {}).get("proteins_100g", "Ukjent"),
                "fat_per_100g": product.get("nutriments", {}).get("fat_100g", "Ukjent"),
                "carbohydrates_per_100g": product.get("nutriments", {}).get("carbohydrates_100g", "Ukjent"),
                "weight": product.get("product_quantity", "Ukjent"),
                "image_url": product.get("image_url", None),
                "source": "Open Food Facts",
                "is_favorite": False
            }
            for product in data.get("products", []) if product.get("product_name")
        ]
    except requests.exceptions.RequestException as e:
        print(f"Feil ved forespørsel til Open Food Facts: {e}")  # Debugging
        flash("Kunne ikke hente resultater fra Open Food Facts.", "danger")
        return []


def fetch_kassal_products(query, page_size=10):
    url = "https://kassal.app/api/v1/products"
    params = {"search": query, "size": page_size}
    headers = {"Authorization": f"Bearer {KASSAL_API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Sjekk om vi får produkter
        if "data" not in data or not data["data"]:
            print("Ingen produkter funnet i Kassal API")
            return []

        kassal_products = []
        for product in data["data"]:
            nutrition = {n["code"]: n["amount"] for n in product.get("nutrition", [])}

            kassal_products.append({
                "id": None,
                "name": product.get("name", "Ukjent produkt"),
                "calories_per_100g": nutrition.get("energi_kcal", "Ukjent"),
                "proteins_per_100g": nutrition.get("protein", "Ukjent"),
                "fat_per_100g": nutrition.get("fett_totalt", "Ukjent"),
                "carbohydrates_per_100g": nutrition.get("karbohydrater", "Ukjent"),
                "weight": product.get("weight") if product.get("weight") else "Ukjent",
                "image_url": product.get("image") if product.get("image") else None,
                "source": "Kassal.app",
                "is_favorite": False
            })

        return kassal_products

    except requests.exceptions.RequestException as e:
        print(f"Feil ved forespørsel til Kassal API: {e}")
        return []



@app.route('/add_favorite_open_food', methods=['POST'])
@login_required
def add_favorite_open_food():
    """Lar brukeren legge til et produkt fra Open Food Facts i favorittlisten med ønsket mengde gram"""
    name = request.form.get('name')
    gram = float(request.form.get('gram', 100))  # Standardverdi 100g
    calories_per_100g = float(request.form.get('calories', 0))
    proteins_per_100g = float(request.form.get('proteins', 0))
    fat_per_100g = float(request.form.get('fat', 0))
    carbohydrates_per_100g = float(request.form.get('carbohydrates', 0))
    image_url = request.form.get('image', '')

    if gram <= 0:
        flash("Mengden må være større enn null.", "danger")
        return redirect(url_for('search'))

    # Beregn næringsinnhold for valgt gram
    calories = (calories_per_100g * gram) / 100
    proteins = (proteins_per_100g * gram) / 100
    fat = (fat_per_100g * gram) / 100
    carbohydrates = (carbohydrates_per_100g * gram) / 100

    # Opprett nytt favorittprodukt i databasen
    new_fav_product = Product(
        name=name,
        weight=gram,
        calories=calories,
        proteins=proteins,
        fat=fat,
        carbohydrates=carbohydrates,
        image=image_url  # Lagre bildet fra Open Food Facts
    )

    db.session.add(new_fav_product)
    db.session.commit()
    
    flash(f"Produktet '{name}' ble lagt til favoritter med {gram}g!", "success")
    return redirect(url_for('search'))


@app.route('/add_to_tracker', methods=['POST'])
@login_required
def add_to_tracker():
    print("🔍 Received form data:", request.form)

    # Navn på produktet
    name = request.form.get('name', 'Ukjent produkt').strip()

    # Brukeren oppgir porsjonsmengde
    portion_str = request.form.get('weight', '0').strip()

    # Opprinnelig totalvekt, for å finne riktig Product-rad
    original_weight_str = request.form.get('original_weight', '').strip()

    # Næringsinnhold per 100g
    cals_str = request.form.get('calories_per_100g', '0').strip()
    prot_str = request.form.get('proteins_per_100g', '0').strip()
    fat_str  = request.form.get('fat_per_100g', '0').strip()
    carb_str = request.form.get('carbohydrates_per_100g', '0').strip()

    try:
        portion = float(portion_str) if portion_str else 0
        original_weight = float(original_weight_str) if original_weight_str else 0
        cals100 = float(cals_str) if cals_str else 0
        prot100 = float(prot_str) if prot_str else 0
        fat100  = float(fat_str)  if fat_str  else 0
        carb100 = float(carb_str) if carb_str else 0
    except ValueError:
        flash("Ugyldige tallverdier i skjema!", "danger")
        return redirect(url_for('index'))

    if portion <= 0:
        flash("Porsjonsmengden må være større enn null!", "danger")
        return redirect(url_for('index'))

    # Beregn total næringsinfo for porsjonen
    total_calories = round((cals100 * portion) / 100, 1)
    total_proteins = round((prot100 * portion) / 100, 1)
    total_fat       = round((fat100  * portion) / 100, 1)
    total_carbs     = round((carb100 * portion) / 100, 1)

    # Finn eller opprett DayLog
    selected_date = session.get('selected_date', date.today().isoformat())
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()

    day_log = DayLog.query.filter_by(date=selected_date, user_id=current_user.id).first()
    if not day_log:
        day_log = DayLog(date=selected_date, user_id=current_user.id)
        db.session.add(day_log)
        db.session.commit()

    # Oppdater eller opprett en LogEntry
    existing_entry = LogEntry.query.filter_by(day_id=day_log.id, name=name).first()
    if existing_entry:
        existing_entry.weight        += portion
        existing_entry.calories      += total_calories
        existing_entry.proteins      += total_proteins
        existing_entry.fat           += total_fat
        existing_entry.carbohydrates += total_carbs
    else:
        new_log_entry = LogEntry(
            day_id=day_log.id,
            name=name,
            weight=portion,
            calories=total_calories,
            proteins=total_proteins,
            fat=total_fat,
            carbohydrates=total_carbs
        )
        db.session.add(new_log_entry)

    # ----------------------------
    # 1) Finn Product-raden lokalt
    # ----------------------------
    product = None
    if original_weight > 0:
        # Søker på både navn og totalvekt
        product = Product.query.filter_by(name=name, weight=original_weight).first()
        if not product:
            print(f"⚠️ Fant ingen Product med name={name} og weight={original_weight}.")
    else:
        # fallback hvis original_weight=0
        product = Product.query.filter_by(name=name).first()

    # Oppdater / opprett UserLoggedProduct
    if product:
        existing_logged_product = UserLoggedProduct.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()
        if existing_logged_product:
            existing_logged_product.times_selected += 1
            existing_logged_product.last_selected = datetime.utcnow()
        else:
            new_logged_product = UserLoggedProduct(
                user_id=current_user.id,
                product_id=product.id,
                times_selected=1,
                last_selected=datetime.utcnow()
            )
            db.session.add(new_logged_product)
    else:
        print(f"⚠️ Ingen lokal Product-rad funnet for '{name}' med original_weight={original_weight} (valgfritt)")

    # ---------------------------------
    # 2) Oppdater / opprett SelectedProduct
    # ---------------------------------
    selected_product = SelectedProduct.query.filter_by(
        user_id=current_user.id,
        product_name=name
    ).first()

    if selected_product:
        # Øk times_selected
        selected_product.times_selected += 1
        selected_product.last_selected = datetime.utcnow()

        # Hvis vi fant Product, sett product_id
        if product:
            selected_product.product_id = product.id

        # Ikke overskriv med portion – bruk original_weight hvis > 0
        if original_weight > 0:
            selected_product.weight = original_weight
    else:
        new_sp = SelectedProduct(
            user_id=current_user.id,
            product_id=product.id if product else None,
            product_name=name,
            calories_per_100g=cals100,
            proteins_per_100g=prot100,
            fat_per_100g=fat100,
            carbohydrates_per_100g=carb100,
            weight=original_weight if original_weight > 0 else None,
            image_url=request.form.get('image_url') or url_for('static', filename='upload/default_image.png'),
            times_selected=1,
            last_selected=datetime.utcnow()
        )
        db.session.add(new_sp)

    db.session.commit()
    flash(f"{portion} g av {name} er lagt til for {selected_date}.", "success")
    return redirect(url_for('index', date=selected_date.isoformat()))




@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)  # Sikkerhet: Bruk get_or_404 for å unngå at ugyldige ID-er gir uventet oppførsel.
    
    # 🔥 Slett alle referanser i `user_logged_product` før produktet slettes
    UserLoggedProduct.query.filter_by(product_id=product_id).delete()

    # Slett bildet fra serveren hvis det finnes
    if product.image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image.split('/')[-1])  # Finn full sti til bildet
        if os.path.exists(image_path):  # Sjekk om filen eksisterer
            try:
                os.remove(image_path)  # Slett filen
            except Exception as e:
                flash(f"Kunne ikke slette bildet: {str(e)}", 'warning')
    
    # Slett produktet fra databasen
    db.session.delete(product)
    db.session.commit()

    flash(f"Produktet '{product.name}' ble slettet.", 'success')
    return redirect(url_for('manage_products'))




@app.route('/delete_daily_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_daily_entry(entry_id):
    # Finn loggføringen basert på ID
    log_entry = LogEntry.query.get_or_404(entry_id)
    
    # Hent loggens dag
    day_log = log_entry.day

    # Oppdater daglige totaler
    day_log.entries.remove(log_entry)

    # Slett loggføringen fra databasen
    db.session.delete(log_entry)
    db.session.commit()

    flash(f"'{log_entry.name}' ble fjernet fra dagens logg.", 'success')
    return redirect(url_for('index', date=day_log.date))

@app.route('/manage_products', methods=['GET', 'POST'])
@login_required
def manage_products():
    if request.method == 'POST':
        # Hent data fra skjemaet
        name = request.form.get('name', '').strip()
        try:
            weight = float(request.form.get('weight', 0))
            proteins_per_100g = float(request.form.get('proteins_per_100g', 0))
            fat_per_100g = float(request.form.get('fat_per_100g', 0))
            carbohydrates_per_100g = float(request.form.get('carbohydrates_per_100g', 0))
        except ValueError:
            flash("Alle numeriske verdier må være gyldige tall.", "danger")
            return redirect(url_for('manage_products'))

        if weight <= 0:
            flash("Totalvekten må være større enn null.", "danger")
            return redirect(url_for('manage_products'))

        # Beregn kalorier automatisk
        calories_per_100g = (
            (proteins_per_100g * 4)
            + (fat_per_100g * 9)
            + (carbohydrates_per_100g * 4)
        )

        # Håndter bildeopplasting
        image = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                # Sørg for at opplastingsmappen finnes
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

                # Opprett et sikkert filnavn
                secure_name = secure_filename(image_file.filename)

                # Lagre bildet fysisk
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
                image_file.save(image_path)

                # NB! Lagre i databasen med "uploads/"-prefiks
                image = f"uploads/{secure_name}"

        # Sjekk om produktet allerede finnes (brukerskapt)
        existing_product = Product.query.filter_by(name=name, created_by_user=True).first()
        if existing_product:
            flash(f"Produktet '{name}' finnes allerede i databasen!", 'warning')
            return redirect(url_for('manage_products'))

        # Opprett og lagre nytt brukeropprettet produkt
        new_product = Product(
            name=name,
            weight=weight,
            calories=(calories_per_100g * weight) / 100,
            proteins=(proteins_per_100g * weight) / 100,
            fat=(fat_per_100g * weight) / 100,
            carbohydrates=(carbohydrates_per_100g * weight) / 100,
            image=image,  # Her lagres stien "uploads/filnavn.jpg"
            created_by_user=True,
            approved=False  # Ikke godkjent av admin ennå
        )
        db.session.add(new_product)
        db.session.commit()

        flash(f"Produktet '{name}' er lagt til, men ikke godkjent ennå.", "info")
        return redirect(url_for('manage_products'))

    # Viser kun brukerskapte produkter (om du vil filtrere på eier, legg til user_id her)
    user_created_products = Product.query.filter_by(created_by_user=True).all()

    return render_template(
        'manage_products.html',
        products=user_created_products
    )



@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        try:
            # Oppdater navn og vekt
            product.name = request.form.get('name', '').strip()
            product.weight = float(request.form.get('weight', 0))
            if product.weight <= 0:
                raise ValueError("Totalvekten må være større enn null.")

            # Hent næringsverdier per 100g
            proteins_per_100g = float(request.form.get('proteins_per_100g', 0))
            fat_per_100g = float(request.form.get('fat_per_100g', 0))
            carbohydrates_per_100g = float(request.form.get('carbohydrates_per_100g', 0))

            # Valider
            if proteins_per_100g < 0 or fat_per_100g < 0 or carbohydrates_per_100g < 0:
                raise ValueError("Næringsverdier kan ikke være negative.")

            # Oppdater totale næringsverdier
            product.proteins = (proteins_per_100g * product.weight) / 100
            product.fat = (fat_per_100g * product.weight) / 100
            product.carbohydrates = (carbohydrates_per_100g * product.weight) / 100

            # Oppdater kalorier
            product.calories = (
                (product.proteins * 4)
                + (product.fat * 9)
                + (product.carbohydrates * 4)
            )

            # Håndter bildeopplasting (hvis nytt bilde er valgt)
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    filename = secure_filename(image_file.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image_file.save(image_path)

                    # Oppdater databasen med "uploads/<filnavn>"
                    product.image = f"uploads/{filename}"

            db.session.commit()
            flash(f"Produktet '{product.name}' ble oppdatert!", 'success')
            return redirect(url_for('manage_products'))

        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for('edit_product', product_id=product.id))

        except Exception:
            flash("Uforventet feil oppstod. Prøv igjen.", "danger")
            return redirect(url_for('edit_product', product_id=product.id))

    # GET: Vis skjema
    return render_template('edit_product.html', product=product)


@app.route('/admin/unapproved_products', methods=['GET'])
@login_required
def unapproved_products():
    if not current_user.is_admin:
        flash("Du har ikke tilgang til denne siden.", "danger")
        return redirect(url_for('index'))

    products = Product.query.filter_by(created_by_user=True, approved=False).all()
    return render_template('admin_unapproved.html', products=products)

@app.route('/admin/approve_product/<int:product_id>', methods=['POST'])
@login_required
def approve_product(product_id):
    if not current_user.is_admin:
        flash("Ingen tilgang!", "danger")
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    product.approved = True
    db.session.commit()

    flash(f"Produkt '{product.name}' er nå godkjent!", "success")
    return redirect(url_for('unapproved_products'))



@app.route('/day_log/<string:date>', methods=['GET'])
@login_required
def day_log(date):
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        flash("Ugyldig datoformat.", "danger")
        return redirect(url_for('index'))

    # Finn DayLog for valgt dato
    day_log_obj = DayLog.query.filter_by(date=selected_date, user_id=current_user.id).first()
    if not day_log_obj:
        flash("Ingen logg funnet for valgt dato.", "info")
        return redirect(url_for('index'))

    # Summer opp dagens totaler
    day_totals = {
        'calories': sum(e.calories for e in day_log_obj.entries),
        'proteins': sum(e.proteins for e in day_log_obj.entries),
        'fat': sum(e.fat for e in day_log_obj.entries),
        'carbohydrates': sum(e.carbohydrates for e in day_log_obj.entries),
    }

    # Hent brukerens mål
    user_goal = UserGoal.query.filter_by(user_id=current_user.id).first()
    goal_type = user_goal.goal_type if user_goal else "Ukjent"

    # Funksjon som vurderer om dagens tall samsvarer med målet
    def evaluate_goals(day_totals, user_goal, goal_type):
        feedback = {}
        if not user_goal:
            feedback["Kalorier"] = "Ukjent"
            feedback["Proteiner"] = ""
            feedback["Total"] = "Ingen mål er satt"
            return feedback

        protein_ok = (day_totals['proteins'] >= (user_goal.protein_goal or 0))

        if goal_type == "Kaloriunderskudd":
            calories_ok = (day_totals['calories'] <= (user_goal.calorie_goal or 0))
            feedback["Kalorier"]  = "✅ Treffet!" if calories_ok else "❌ For høyt!"
            feedback["Proteiner"] = "✅ Treffet!" if protein_ok else "❌ For lavt!"
            feedback["Total"]     = "✅ Bra dag i underskudd!" if (calories_ok and protein_ok) else "⚠️ Juster litt."

        elif goal_type == "Kalorioverskudd":
            calories_ok = (day_totals['calories'] >= (user_goal.calorie_goal or 0))
            feedback["Kalorier"]  = "✅ Treffet!" if calories_ok else "❌ For lavt!"
            feedback["Proteiner"] = "✅ Treffet!" if protein_ok else "❌ For lavt!"
            feedback["Total"]     = "✅ Bra bulking-dag!" if (calories_ok and protein_ok) else "⚠️ Juster for bedre muskelvekst."

        elif goal_type == "Vedlikehold":
            margin = 200
            c_min = (user_goal.calorie_goal or 0) - margin
            c_max = (user_goal.calorie_goal or 0) + margin
            calories_ok = (day_totals['calories'] >= c_min) and (day_totals['calories'] <= c_max)
            feedback["Kalorier"]  = "✅ Perfekt!" if calories_ok else "⚠️ Juster litt."
            feedback["Proteiner"] = "✅ Treffet!" if protein_ok else "❌ For lavt!"
            feedback["Total"]     = "✅ Perfekt balanse!" if (calories_ok and protein_ok) else "⚠️ Juster litt."

        else:
            feedback["Kalorier"] = "Ingen måltype definert"
            feedback["Proteiner"] = ""
            feedback["Total"] = "Ingen måltype definert"

        return feedback

    # Vurder dagens inntak
    goal_feedback = evaluate_goals(day_totals, user_goal, goal_type)

    # Framgang: hvor mange dager logget, hvor mange “møtt” målet
    goal_tracking = {'total_days': 0, 'days_met': 0}
    if user_goal:
        all_logs = DayLog.query.filter_by(user_id=current_user.id).all()
        goal_tracking['total_days'] = len(all_logs)

        def meets_goal(log_totals, user_goal, goal_type):
            gf = evaluate_goals(log_totals, user_goal, goal_type)
            return gf.get("Total") in [
                "✅ Bra dag i underskudd!",
                "✅ Bra bulking-dag!",
                "✅ Perfekt balanse!"
            ]

        for dl in all_logs:
            dl_totals = {
                'calories': sum(e.calories for e in dl.entries),
                'proteins': sum(e.proteins for e in dl.entries),
                'fat': sum(e.fat for e in dl.entries),
                'carbohydrates': sum(e.carbohydrates for e in dl.entries),
            }
            if meets_goal(dl_totals, user_goal, goal_type):
                goal_tracking['days_met'] += 1

    # Lag strenger for forrige/neste dag
    next_date_obj = selected_date + timedelta(days=1)
    prev_date_obj = selected_date - timedelta(days=1)
    next_date_str = next_date_obj.strftime("%Y-%m-%d")
    prev_date_str = prev_date_obj.strftime("%Y-%m-%d")

    return render_template(
        'day_log.html',
        day_log=day_log_obj,
        day_totals=day_totals,
        selected_date=selected_date,
        next_date_str=next_date_str,
        prev_date_str=prev_date_str,
        goal_feedback=goal_feedback,
        goal_tracking=goal_tracking,
        user_goal=user_goal,
        goal_type=goal_type
    )



@app.route('/legg_til_kaloriteller', methods=['POST'])
@login_required
def legg_til_kaloriteller():
    data = request.json
    navn = data['navn']
    kalorier = float(data.get('kalorier', 0))
    protein = float(data.get('protein', 0))
    fett = float(data.get('fett', 0))
    karbo = float(data.get('karbo', 0))
    mengde = float(data.get('mengde', 100))

    selected_date = session.get('selected_date', date.today().isoformat())
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()

    # Finn eller opprett logg for dagen
    day_log = DayLog.query.filter_by(date=selected_date, user_id=current_user.id).first()
    if not day_log:
        day_log = DayLog(date=selected_date, user_id=current_user.id)
        db.session.add(day_log)

    nytt_produkt = LogEntry(
        day=day_log,
        name=navn,
        calories=(kalorier * mengde) / 100,
        proteins=(protein * mengde) / 100,
        fat=(fett * mengde) / 100,
        carbohydrates=(karbo * mengde) / 100,
        weight=mengde
    )

    db.session.add(nytt_produkt)
    db.session.commit()

    return jsonify({'status': 'success'})


@app.route('/scan')
def scan():
    # Viser HTML-siden med Quagga
    return render_template('barcode_scanner.html')

@app.route('/barcode_lookup', methods=['POST'])
def barcode_lookup():
    data = request.json
    barcode = data.get('barcode')

    # Først søk i Open Food Facts
    off_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(off_url)
    off_data = response.json()

    if off_data.get('status') == 1:
        product = {
            'name': off_data['product'].get('product_name', 'Ukjent produkt'),
            'calories': off_data['product']['nutriments'].get('energy-kcal_100g', ''),
            'protein': off_data['product']['nutriments'].get('proteins_100g', ''),
            'fat': off_data['product']['nutriments'].get('fat_100g', ''),
            'carbs': off_data['product']['nutriments'].get('carbohydrates_100g', ''),
            'image': off_data['product'].get('image_front_url', '')
        }
        return jsonify({'status': 'success', 'data': product})

    # Hvis ikke funnet i OFF, søk i Kassal.app
    kassal_url = f"https://kassal.app/api/v1/products/ean/{barcode}"
    headers = {'Authorization': 'Bearer LPqw5vGJeRBBEMns35N9qCyHYvvMbpDcqQTIwkPJ'}
    kassal_response = requests.get(kassal_url, headers=headers)
    kassal_data = kassal_response.json()

    if kassal_response.status_code == 200 and kassal_data.get('data'):
        product = kassal_data['data']
        return jsonify({'status': 'success', 'data': {
            'name': product.get('name', 'Ukjent produkt'),
            'calories': '',  # eventuelt
            'protein': '',
            'fat': '',
            'carbs': '',
            'image': product.get('image', '')
        }})

    # Ingenting funnet
    return jsonify({'status': 'fail', 'message': 'Produktet ble ikke funnet i noen databaser.'})

# Initialize database with app context (må være neders)
if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000, debug=True)