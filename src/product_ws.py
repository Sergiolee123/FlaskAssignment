import hashlib
import json
import socket
import sys
import threading

from flask import (Flask, request, jsonify)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# config the sitting of the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lib//product_data.db"
db = SQLAlchemy(app)
# use a lock to control the write access to the database
lock = threading.Lock()
# config the TCP target to get the daytime fo server exe_id
HOST = "time-b-b.nist.gov"
PORT = 13
# use to store the server exe_id
exe_id = None


# generate the server exe_id
def get_exe_id(host, port):
    # connect to the daytime TCP server to get the daytime
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        file = s.makefile()
        line = file.readline()
        # use the bytes data of the daytime string to generate server exe_id
        return hashlib.sha256(line.encode('utf-8')).hexdigest()


# product attributes of the database table
class Product(db.Model):
    # The id will auto increment if there is new item created
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    desc = db.Column(db.String(80), nullable=False)
    unit_price = db.Column(db.Integer(), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)


# The route for querying a product
@app.route("/api/query", methods=["POST"])
def product_query():
    data = json.loads(request.data)
    try:
        id = check_id(data.get("id"))
    except:
        return jsonify("The id should be an integer of zero or a positive value"), 400
    # The database auto increment starts from 1, so to start with id: 0,
    # the server needs to add the id by 1 for the id mapping
    item = Product.query.get(id + 1)
    if not item:
        return jsonify(f"The product with id:{id} does not exist"), 404
    # The database auto increment starts from 1, so to start with id: 0,
    # the server needs to delete the id by 1 for the id mapping
    return {"exe_id": exe_id, "id": item.id - 1, "desc": item.desc, "unit_price": item.unit_price,
            "quantity": item.quantity}


# The route for buying a product
@app.route("/api/purchase", methods=["POST"])
def product_purchase():
    data = json.loads(request.data)
    try:
        id = check_id(data.get("id"))
    except:
        return jsonify("The id should be an integer of zero or a positive value"), 400
    quantity = check_quantity(data.get("quantity"), "purchase")
    card = str(data.get("card"))
    # return the error JSON if the quantity is not a integer
    if type(quantity) != int:
        return quantity
    # The length of the card number should equals to 16
    if not card or not card.strip() or len(card) != 16:
        return jsonify(f"The card number should be 16 digits"), 400
    # gain lock to avoid another thread update the database when updating it
    with lock:
        # The database auto increment starts from 1, so to start with id: 0,
        # the server needs to add the id by 1 for the id mapping
        item = Product.query.get(id + 1)
        if not item:
            return jsonify(f"The product with id:{id} does not exist"), 404
        # check whether the stock is sufficient
        if quantity > item.quantity:
            return jsonify(f"The product {item.desc} is only left {item.quantity} in stock"), 404
        # calculate the amount of the payment
        amount = quantity * item.unit_price
        # update the stock
        item.quantity = item.quantity - quantity
        db.session.commit()
    return {"exe_id": exe_id, "amount": amount}



@app.route("/api/replenish", methods=["POST"])
def product_replenish():
    data = json.loads(request.data)
    try:
        id = check_id(data.get("id"))
    except:
        return jsonify("The id should be an integer of zero or a positive value"), 400

    quantity = check_quantity(data.get("quantity"), "replenish")
    # return the error JSON if the quantity is not a integer
    if type(quantity) != int:
        return quantity
    # gain lock to avoid another thread update the database when updating it
    with lock:
        # The database auto increment starts from 1, so to start with id: 0,
        # the server needs to add the id by 1 for the id mapping
        item = Product.query.get(id + 1)
        if not item:
            return jsonify(f"The product with id:{id} does not exist"), 404
        item.quantity = item.quantity + quantity
        db.session.commit()
    return {"exe_id": exe_id, "status": "success"}


# check the validation of the id
def check_id(data):
    # Check whether the id is an integer, raise an exception if not.
    id = int(data)
    # The id should not be empty or smaller than 0
    if id is None or id < 0:
        raise
    else:
        # if valid, return the id
        return id


# check the validation of the check_quantity
def check_quantity(data, action):
    try:
        # Check whether the quantity is an integer, raise an exception if not.
        quantity = int(data)
    except:
        return jsonify("The quantity should be an integer"), 400
    # Check whether the quantity is empty or <= 0
    if not quantity or quantity <= 0:
        return jsonify(f"At least one quantity should be {action}"), 400
    # if valid, return the id
    return quantity


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else PORT
    # get the exe_id when the server program starts
    exe_id = get_exe_id(host, port)
    app.run()
