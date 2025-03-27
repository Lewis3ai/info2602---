import os
import csv
import datetime
from flask import Flask, request, redirect, render_template, url_for, flash, jsonify
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
    current_user,
    get_jwt_identity
)
from App.models import db, User, UserPokemon, Pokemon

# Configure Flask App
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'MySecretKey'
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=15)
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config['JWT_HEADER_NAME'] = "Cookie"

# Initialize App 
db.init_app(app)
app.app_context().push()
CORS(app)
jwt = JWTManager(app)

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)

# ********** Initialize Database **************

def initialize_db():
    db.drop_all()
    db.create_all()
    with open('pokemon.csv', newline='', encoding='utf8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['height_m'] == '':
                row['height_m'] = None
            if row['weight_kg'] == '':
                row['weight_kg'] = None
            if row['type2'] == '':
                row['type2'] = None

            pokemon = Pokemon(
                name=row['name'],
                attack=row['attack'],
                defense=row['defense'],
                sp_attack=row['sp_attack'],
                sp_defense=row['sp_defense'],
                weight=row['weight_kg'],
                height=row['height_m'],
                hp=row['hp'],
                speed=row['speed'],
                type1=row['type1'],
                type2=row['type2']
            )
            db.session.add(pokemon)

        bob = User(username='bob', email="bob@mail.com", password="bobpass")
        db.session.add(bob)
        db.session.commit()
        bob.catch_pokemon(1, "Benny")
        bob.catch_pokemon(25, "Saul")

# ********** Routes **************

@app.route('/init')
def init_route():
    initialize_db()
    return redirect(url_for('login_page'))

@app.route("/", methods=['GET'])
def login_page():
    return render_template("login.html")

@app.route("/signup", methods=['GET'])
def signup_page():
    return render_template("signup.html")

@app.route("/signup", methods=['POST'])
def signup_action():
    try:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user)
        response = redirect(url_for('home_page'))
        set_access_cookies(response, token)
        flash('Account created successfully!')
        return response
    except IntegrityError:
        db.session.rollback()
        flash('Username already exists')
        return redirect(url_for('signup_page'))

@app.route("/logout", methods=['GET'])
@jwt_required()
def logout_action():
    response = redirect(url_for('login_page'))
    unset_jwt_cookies(response)
    flash('Logged out')
    return response

@app.route("/app", methods=['GET'])
@app.route("/app/<int:pokemon_id>", methods=['GET'])
@jwt_required()
def home_page(pokemon_id=1):
    pokemon_list = Pokemon.query.all()
    selected_pokemon = Pokemon.query.get(pokemon_id)
    user_pokemon = UserPokemon.query.filter_by(user_id=get_jwt_identity()).all()
    return render_template("home.html", pokemon_list=pokemon_list, selected_pokemon=selected_pokemon, user_pokemon=user_pokemon)

@app.route("/login", methods=['POST'])
def login_action():
    username = request.form["username"]
    password = request.form["password"]
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        response = redirect(url_for("home_page"))
        token = create_access_token(identity=user)
        set_access_cookies(response, token)
        return response
    else:
        flash("Invalid credentials")
        return redirect(url_for("login_page"))

@app.route("/pokemon/<int:pokemon_id>", methods=['POST'])
@jwt_required()
def capture_action(pokemon_id):
    user = User.query.get(get_jwt_identity())
    user.catch_pokemon(pokemon_id, f"Pokemon-{pokemon_id}")
    flash("Pokemon Captured!")
    return redirect(url_for("home_page"))

@app.route("/rename-pokemon/<int:pokemon_id>", methods=['POST'])
@jwt_required()
def rename_action(pokemon_id):
    user = User.query.get(get_jwt_identity())
    new_name = request.form["name"]
    user.rename_pokemon(pokemon_id, new_name)
    flash("Pokemon Renamed!")
    return redirect(url_for("home_page"))

@app.route("/release-pokemon/<int:pokemon_id>", methods=['GET'])
@jwt_required()
def release_action(pokemon_id):
    user = User.query.get(get_jwt_identity())
    user.release_pokemon(pokemon_id)
    flash("Pokemon Released!")
    return redirect(url_for("home_page"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)