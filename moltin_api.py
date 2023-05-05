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
        if not hasattr(self, '_price_book_id'):
            self._price_book_id = kwargs['price_book_id']
        self._get_token()

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
            self._token_obj = response.json()
        return self._token_obj

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

    def get_product_with_price(self, product_id: str):
        product = self.get_product(product_id)
        price_book = self._get_price_book()
        current_product_in_price_book = next(filter(
            lambda p: p['attributes']['sku'] == product['data']['attributes']['sku'],
            price_book['included']
        ))
        product['data']['price'] = current_product_in_price_book['attributes']['currencies']['RUB']['amount'] / 100
        return product

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

    def get_customer_carts(self, customer_email: str) -> dict:
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

    def get_current_cart_id(self, customer_email: str):
        customer_carts = self.get_customer_carts(customer_email)
        if not customer_carts['data']:
            cart_id = self._create_cart(customer_email)['data']['id']
        else:
            cart_id = customer_carts['data'][0]['id']
        return cart_id

    def get_current_cart(self, customer_email: str) -> dict:
        cart_id = self.get_current_cart_id(customer_email)
        return self.get_cart_items(cart_id)

    def add_product_to_cart(self, product_id: str, quantity: int, customer_email: str) -> str:
        cart_id = self.get_current_cart_id(customer_email)
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

    def delete_product_from_cart(self, cart_id: str, product_id: str):
        url = f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        response = requests.delete(url, headers=headers)
        check_response(response)

    def _create_cart(self, customer_email: str) -> dict:
        url = 'https://api.moltin.com/v2/carts'
        headers = {
            'Authorization': self._get_token()['access_token'],
            'x-moltin-customer-token': self._get_customer_token(customer_email)
        }
        response = requests.post(url, json={'data': {'name': 'Cart'}}, headers=headers)
        check_response(response)
        return response.json()

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

    def _get_price_book(self) -> dict:
        url = f'https://api.moltin.com/pcm/pricebooks/{self._price_book_id}'
        headers = {
            'Authorization': self._get_token()['access_token']
        }
        params = {
            'include': 'prices'
        }
        response = requests.get(url, headers=headers, params=params)
        check_response(response)
        return response.json()


def check_response(response: requests.Response):
    if 'errors' in response.text:
        raise requests.exceptions.HTTPError(response.text)
    response.raise_for_status()
