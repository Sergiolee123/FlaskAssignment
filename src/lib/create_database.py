import json
import random
import threading
import time
from urllib.request import urlopen

from flask import (Flask, jsonify)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///product_data.db"
db = SQLAlchemy(app)


# This program is used to create the database
# product attributes of the database table
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desc = db.Column(db.String(80), nullable=False)
    unit_price = db.Column(db.Integer(), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)

# use a get request to set up the database
@app.route("/setup")
def product_setup():
    # The description of each product
    product_name = ["apple", "hangbag", "clothes", "banana", "lemon", "shoes", "TV", "headsets", "toys", "chairs"]
    # randomly create other attributes of the table
    products = [Product(desc=product_name[i], unit_price=random.randint(i, 20), quantity=random.randint(i, 50))
     for i in range(10)]
    for item in products:
        db.session.add(item)
        db.session.commit()
    products = []
    for item in Product.query.all():
        products.append(product_to_json(item))
    return jsonify(products)


def product_to_json(item):
    return {"id": item.id, "desc": item.desc, "unit_price": item.unit_price, "quantity": item.quantity}

def create_db():
    # wait for the server start
    time.sleep(10)
    # send the request to create the database
    with urlopen(f"http://localhost:5000/setup") as resp:
        json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    # create the database table
    db.create_all()
    # use a thread to send the create get request
    threading.Thread(target=create_db).start()
    app.run()
