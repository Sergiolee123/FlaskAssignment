import json, unittest
import math
import os
import random
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SERVER = "localhost:5000"
# A valid card number used for testing
VALID_CARD = "ASCEESDQFOGKSD1F"
# An invalid card number used for testing
INVALID_CARD = "card"


# client used to send request to the server
def ws_client(url, data):
    data = json.dumps(data).encode("utf-8")
    headers = {"Content-type": "application/json; charset=UTF-8"}
    req = Request(url=url, data=data, headers=headers, method="POST")
    with urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result


class TestTodoServer(unittest.TestCase):
    # set up the web server as a sub process for testing
    @classmethod
    def setUpClass(cls):
        this_file_dir = os.path.dirname(__file__)
        cls.server_proc = subprocess.Popen(
            ["python", "product_ws.py"], cwd=f"{this_file_dir}/../src")
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server_proc.terminate()


    def test_query_product(self):
        # all the description of the database
        product_desc = ["apple", "hangbag", "clothes", "banana", "lemon", "shoes", "TV",
                        "headsets", "toys", "chairs"]
        id = random.randint(0, 9)
        query_result = ws_client(f"http://{SERVER}/api/query", {"id": id})
        # The query result product description should be same as the list
        self.assertEqual(product_desc[id], query_result["desc"])

    def test_buy_product_sufficient(self):
        """
        randomly pick a product and check its quantity
        check whether there is any quantity, if no, replenish it to make sure there is quantity
        So that the server can perform buying test
        """
        while True:
            id = random.randint(0, 9)
            product_before_buy = ws_client(f"http://{SERVER}/api/query", {"id": id})
            if product_before_buy["quantity"] > 0:
                break
            else:
                ws_client(f"http://{SERVER}/api/replenish", {"id": id, "quantity": 10})
        product_price = product_before_buy["unit_price"]
        # buy a product with sufficient quantity
        quantity = random.randint(1, product_before_buy["quantity"])
        buy_request = {"id": id, "quantity": quantity, "card": VALID_CARD}
        buy_result = ws_client(f"http://{SERVER}/api/purchase", buy_request)
        # get the product data after buying
        product_after_buy = ws_client(f"http://{SERVER}/api/query", {"id": id})
        # The amount should be correctly payed
        self.assertEqual(buy_result["amount"], quantity * product_price)
        # The quantity should be correctly updated
        self.assertEqual(product_before_buy["quantity"] - quantity, product_after_buy["quantity"])

    def test_buy_product_insufficient(self):
        # randomly buy a product and check its quantity
        id = random.randint(0, 9)
        # get the product data before buying
        product_before_buy = ws_client(f"http://{SERVER}/api/query", {"id": id})
        # buy a product with insufficient quantity
        quantity = product_before_buy["quantity"] + 1
        buy_request = {"id": id, "quantity": quantity, "card": VALID_CARD}
        try:
            ws_client(f"http://{SERVER}/api/purchase", buy_request)
            self.assertTrue(False)
        except HTTPError as e:
            # The server should return a 404 error
            self.assertEqual(404, e.code)
        # get the product data after buying failed
        product_after_buy = ws_client(f"http://{SERVER}/api/query", {"id": id})
        # The quantity should be the same
        self.assertEqual(product_before_buy["quantity"], product_after_buy["quantity"])

    def test_replenish_product(self):
        # randomly choose a product and check its quantity
        id = random.randint(0, 9)
        product_before_replenish = ws_client(f"http://{SERVER}/api/query", {"id": id})
        old_quantity = product_before_replenish["quantity"]
        # replenish 10 unit of the product
        quantity = 10
        result = ws_client(f"http://{SERVER}/api/replenish", {"id": id, "quantity": quantity})
        # check whether the replenish success
        self.assertEqual("success", result["status"])
        # The quantity should be updated
        product_after_replenish = ws_client(f"http://{SERVER}/api/query", {"id": id})
        self.assertEqual(old_quantity + quantity, product_after_replenish["quantity"])

    def test_not_exist_product_id(self):
        # The range id is 0-9, 999 should not exist
        try:
            ws_client(f"http://{SERVER}/api/query", {"id": 999})
            self.assertTrue(False)
        except HTTPError as e:
            # The server should return a 404 error
            self.assertEqual(404, e.code)

    def test_invalid_product_id(self):
        # test the non-positive integer id, string id and empty id
        test_value = [-1, "s", ""]
        for id in test_value:
            try:
                ws_client(f"http://{SERVER}/api/query", {"id": id})
                self.assertTrue(False)
            except HTTPError as e:
                # The server should return a 400 error
                self.assertEqual(400, e.code)

    def test_invalid_product_quantity(self):
        # test the 0 quantity, string value quantity and empty quantity
        test_value = [0, "s", ""]
        for quantity in test_value:
            try:
                ws_client(f"http://{SERVER}/api/replenish", {"id": 0, "quantity": quantity})
                self.assertTrue(False)
            except HTTPError as e:
                # The server should return a 400 error
                self.assertEqual(400, e.code)

    def test_invalid_card_number(self):
        id = {"id": 1}
        # get the product data before buying
        product_before_buy = ws_client(f"http://{SERVER}/api/query", id)
        # buy a product with invalid card number
        buy_request = {"id": id, "quantity": 1, "card": INVALID_CARD}
        try:
            ws_client(f"http://{SERVER}/api/purchase", buy_request)
            self.assertTrue(False)
        except HTTPError as e:
            # The server should return a 400 error
            self.assertEqual(400, e.code)

    def test_replenish_product_fail(self):
        # Test for invalid input of replenish 0 or negative quantity
        id = random.randint(0, 9)
        product_before_replenish = ws_client(f"http://{SERVER}/api/query", {"id": id})
        old_quantity = product_before_replenish["quantity"]
        # test replenish 0 unit ,negative number unit of the product
        test_case = [0, -1]
        for quantity in test_case:
            try:
                ws_client(f"http://{SERVER}/api/replenish", {"id": id, "quantity": quantity})
                self.assertTrue(False)
            except HTTPError as e:
                # The server should return a 400 status
                self.assertEqual(400, e.code)
        # The quantity should not be updated
        product_after_replenish = ws_client(f"http://{SERVER}/api/query", {"id": id})
        self.assertEqual(old_quantity, product_after_replenish["quantity"])
        # replenish not exist id of product
        id = 999
        quantity = 10
        try:
            ws_client(f"http://{SERVER}/api/replenish", {"id": id, "quantity": quantity})
            self.assertTrue(False)
        except HTTPError as e:
            # The server should return a 404 status
            self.assertEqual(404, e.code)

    def test_server_execution_id(self):
        first_request = ws_client(f"http://{SERVER}/api/query", {"id": 1})
        second_request = ws_client(f"http://{SERVER}/api/query", {"id": 2})
        # The server execution id should be same
        self.assertEqual(first_request["exe_id"], second_request["exe_id"])

    def test_server_concurrency_access(self):
        # randomly pick a product and check its quantity
        # check whether there is any quantity, if no, replenish it to make sure there is quantity
        while True:
            id = random.randint(0, 9)
            product = ws_client(f"http://{SERVER}/api/query", {"id": id})
            if product["quantity"] > 0:
                break
            else:
                ws_client(f"http://{SERVER}/api/replenish", {"id": id, "quantity": 10})
        # test the server of buying more than half of the quantity in each request
        # so that the second request must be insufficient
        if product["quantity"] % 2 == 0:
            test_quantity = product["quantity"] / 2 + 1
        else:
            test_quantity = math.ceil(product["quantity"] / 2)
        old_quantity = product["quantity"]
        buy_request = {"id": id, "quantity": test_quantity, "card": VALID_CARD}
        # use 2 threads to simulate the concurrent access of the server
        with ThreadPoolExecutor() as executor:
            try:
                buy_request1 = executor.submit(ws_client, f"http://{SERVER}/api/purchase", buy_request)
                buy_request2 = executor.submit(ws_client, f"http://{SERVER}/api/purchase", buy_request)
                # get the result to get the exception
                buy_request1.result()
                buy_request2.result()
                # if there is no HTTP exception for one of the requests, the test fail
                self.assertTrue(False)
            except HTTPError as e:
                # The server should return a 404 status for one of the requests
                self.assertEqual(404, e.code)
        product = ws_client(f"http://{SERVER}/api/query", {"id": id})
        # The quantity should only be update once for one successful buying request
        self.assertEqual(old_quantity - test_quantity, product["quantity"])


if __name__ == "__main__":
    unittest.main()
