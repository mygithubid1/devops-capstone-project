"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import logging
import os
from datetime import date
from unittest import TestCase

from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from tests.factories import AccountFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def ensure_same(self, expected, actual, skip_id_verification=False):
        self.assertEqual(len(expected), len(actual))
        for left, right in zip(expected, actual):
            self.assertEqual(left.name, right.name)
            self.assertEqual(left.email, right.email)
            self.assertEqual(left.address, right.address)
            self.assertEqual(left.phone_number, right.phone_number)
            self.assertEqual(str(left.date_joined), str(right.date_joined))
            if not skip_id_verification:
                self.assertEqual(left.id, right.id)

    def check_get_all_accounts(self, expected):
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        retrieved_accounts = []
        for row in response.get_json():
            account = Account().deserialize(row)
            retrieved_accounts.append(account)
        self.ensure_same(expected, retrieved_accounts)

    def test_list_accounts_with_no_accounts(self):
        """It should list an empty list"""
        self.check_get_all_accounts([])

    def test_list_accounts_with_single_account(self):
        """It should list 1 Account"""
        created_accounts = self._create_accounts(1)
        self.check_get_all_accounts(created_accounts)

    def test_list_accounts_with_multiple_accounts(self):
        """It should list all Accounts"""
        created_accounts = self._create_accounts(3)
        self.check_get_all_accounts(created_accounts)

    def test_get_account_with_no_accounts(self):
        """It should return 404"""
        response = self.client.get(
            f'{BASE_URL}/1',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_account_with_invalid_id(self):
        """It should not get an account with invalid ID"""
        new_account = self._create_accounts(1)[0]
        response = self.client.get(
            f'{BASE_URL}/{new_account.id + 1}',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_account_with_one_account(self):
        """It should get an account by ID"""
        new_account = self._create_accounts(1)[0]
        response = self.client.get(
            f'{BASE_URL}/{new_account.id}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ensure_same([new_account], [Account().deserialize(response.get_json())])

    def test_get_account_with_multiple_accounts(self):
        """It should get an account by ID"""
        new_accounts = self._create_accounts(3)
        for new_account in new_accounts:
            response = self.client.get(
                f'{BASE_URL}/{new_account.id}',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.ensure_same([new_account], [Account().deserialize(response.get_json())])

    def test_invalid_delete_no_accounts(self):
        """It should not delete an account with invalid ID"""
        response = self.client.delete(f'{BASE_URL}/1')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_delete_single_account(self):
        """It should not delete an account with invalid ID"""
        new_account = self._create_accounts(1)[0]
        response = self.client.delete(f'{BASE_URL}/{new_account.id + 1}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_delete_account_multiple_accounts(self):
        """It should delete an account with valid ID"""
        new_accounts = self._create_accounts(1)
        for new_account in new_accounts:
            response = self.client.delete(f'{BASE_URL}/{new_account.id}')
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            response = self.client.get(f'{BASE_URL}/{new_account.id}')
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_with_no_accounts(self):
        """It should return 404"""
        response = self.client.put(
            f'{BASE_URL}/1',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_account_with_nonexistent_account(self):
        """It should not update an account invalid ID"""
        new_account = self._create_accounts(1)[0]
        new_account.name += 'DOES NOT MATTER ...'
        response = self.client.put(
            f'{BASE_URL}/{new_account.id + 1}',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_incorrect_content_type(self):
        """It should not update when content type is incorrect"""
        response = self.client.put(
            f'{BASE_URL}/1',
            content_type="text/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_with_mismatched_id_in_payload(self):
        """It should not update account when account id and underlying update don't match"""
        new_account = self._create_accounts(1)[0]
        new_account_id = new_account.id
        new_account.id += 1
        response = self.client.put(
            f'{BASE_URL}/{new_account_id}',
            content_type='application/json',
            json=new_account.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_with_incorrect_type_id(self):
        """It should not update account when ID is invalid"""
        new_account = self._create_accounts(1)[0]
        new_account_id = new_account.id
        new_account.id = 123.456
        response = self.client.put(
            f'{BASE_URL}/{new_account_id}',
            content_type='application/json',
            json=new_account.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_valid_account(self):
        """It should update a valid account"""
        new_account = self._create_accounts(1)[0]
        new_account.name += ' Changed!'
        response = self.client.put(
            f'{BASE_URL}/{new_account.id}',
            content_type="application/json",
            json=new_account.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ensure_same([new_account], [Account().deserialize(response.get_json())])

    def test_update_proper_date_association(self):
        """It should update proper date association when no date is explicitly set"""
        new_account = self._create_accounts(1)[0]
        serialized = new_account.serialize()
        del serialized['date_joined']
        response = self.client.put(
            f'{BASE_URL}/{new_account.id}',
            content_type="application/json",
            json=serialized
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(date.fromisoformat(response.get_json()['date_joined']), date.today())

    def test_unsupported_http_method(self):
        """It should gracefully handle an unsupported method"""
        response = self.client.patch(f'{BASE_URL}/1')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
