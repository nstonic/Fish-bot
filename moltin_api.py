from datetime import datetime

import requests


class MoltinApiClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if not hasattr(self, '_client_id'):
            self._client_id = kwargs['client_id']
        if not hasattr(self, '_client_secret'):
            self._client_secret = kwargs['client_secret']
        self._token_obj = self._get_token()

    def get_all_products(self) -> dict:
        url = 'https://api.moltin.com/pcm/products'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_product(self, product_id: str) -> dict:
        url = f'https://api.moltin.com/pcm/products/{product_id}'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def fetch_image(self, product_id: str) -> bytes:
        image_id = self._get_image_relationships(product_id)['data']['id']
        image_url = self._get_file_url_by_id(image_id)
        response = requests.get(image_url)
        response.raise_for_status()
        return response.content

    def create_customer(self, email: str) -> dict:
        url = 'https://api.moltin.com/v2/customers'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        payload = {'data': {
            'type': 'customer',
            'name': 'telegram customer',
            'email': email,
            'password': email.split('@')[0]
        }}
        response = requests.post(url, json=payload, headers=headers)
        check_response(response)
        return response.json()

    def get_customer(self, customer_id: str) -> dict:
        url = f'https://api.moltin.com/v2/customers/{customer_id}'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_customers_cart(self, customer_email: str) -> dict:
        url = 'https://api.moltin.com/v2/carts'
        headers = {
            'Authorization': self._get_token()['access_token'],
            'x-moltin-customer-token': self._get_customer_token(customer_email)
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_cart_items(self, cart_id: str) -> dict:
        url = f'https://api.moltin.com/v2/carts/{cart_id}/items'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def _create_cart(self, customer_email: str) -> dict:
        url = 'https://api.moltin.com/v2/carts'
        headers = {
            'Authorization': self._get_token()['access_token'],
            'x-moltin-customer-token': self._get_customer_token(customer_email)
        }
        response = requests.post(url, json={'data': {'name': 'Cart'}}, headers=headers)
        check_response(response)
        return response.json()

    def add_product_to_cart(self, product_id: str, quantity: int, customer_email: str) -> str:
        customer_carts = self.get_customers_cart(customer_email)
        if not customer_carts['data']:
            cart_id = self._create_cart(customer_email)['data']['id']
        else:
            cart_id = customer_carts['data'][0]['id']
        url = f'https://api.moltin.com/v2/carts/{cart_id}/items'
        headers = {
            'Authorization': self._get_token()['access_token'],
            'x-moltin-customer-token': self._get_customer_token(customer_email)
        }
        payload = {'data': {
            'quantity': quantity,
            'type': 'cart_item',
            'id': product_id
        }}
        response = requests.post(url, json=payload, headers=headers)
        check_response(response)
        return cart_id

    def _get_token(self) -> dict:
        now_timestamp = datetime.now().timestamp()
        if not hasattr(self, '_token_obj') or self._token_obj['expires'] - now_timestamp < 300:
            url = 'https://api.moltin.com/oauth/access_token'
            data = {
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client_credentials'
            }
            response = requests.post(url, data=data)
            check_response(response)
            return response.json()
        else:
            return self._token_obj

    def _get_customer_token(self, customer_email: str) -> str:
        url = 'https://api.moltin.com/v2/customers/tokens'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        payload = {'data': {
            'type': 'token',
            'email': customer_email,
            'password': customer_email.split('@')[0],
            'authentication_mechanism': 'password'
        }}
        response = requests.post(url, headers=headers, json=payload)
        check_response(response)
        return response.json()['data']['token']

    def _get_image_relationships(self, product_id: str) -> dict:
        url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def _get_file_url_by_id(self, file_id: str) -> str:
        url = f'https://api.moltin.com/v2/files/{file_id}'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()['data']['link']['href']


def check_response(response: requests.Response):
    if 'errors' in response.text:
        raise requests.exceptions.HTTPError(response.text)
    response.raise_for_status()
