from datetime import datetime

import requests


class MoltinApiClient:

    def __init__(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_obj = self.get_token()

    def get_token(self) -> dict:
        now_timestamp = datetime.now().timestamp()
        if not hasattr(self, '_token_obj') or now_timestamp - self._token_obj['expires'] < 300:
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

    def get_all_products(self) -> dict:
        url = 'https://api.moltin.com/pcm/products'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_product(self, product_id: str) -> dict:
        url = f'https://api.moltin.com/pcm/products/{product_id}'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_image_relationships(self, product_id: str) -> dict:
        url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_file_url_by_id(self, file_id: str) -> str:
        url = f'https://api.moltin.com/v2/files/{file_id}'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()['data']['link']['href']

    def fetch_image(self, product_id: str):
        image_id = self.get_image_relationships(product_id)['data']['id']
        image_url = self.get_file_url_by_id(image_id)
        response = requests.get(image_url)
        response.raise_for_status()
        return response.content

    def create_customer(self, email: str) -> dict:
        url = 'https://api.moltin.com/v2/customers'
        headers = {
            'Authorization': self.get_token()['access_token']
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

    def get_customer(self, customer_id: str):
        url = f'https://api.moltin.com/v2/customers/{customer_id}'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.post(url, headers=headers)
        check_response(response)
        return response.json()

    def get_customer_token(self, customer_email: str) -> str:
        url = 'https://api.moltin.com/v2/customers/tokens'
        headers = {
            'Authorization': self.get_token()['access_token']
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

    def get_customers_cart(self, customer_token: str):
        url = 'https://api.moltin.com/v2/carts'
        headers = {
            'Authorization': self.get_token()['access_token'],
            'x-moltin-customer-token': customer_token
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def get_cart_items(self, cart_ref: str) -> dict:
        url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
        headers = {
            'Authorization': self.get_token()['access_token']
        }
        response = requests.get(url, headers=headers)
        check_response(response)
        return response.json()

    def create_cart(self, customer_token: str):
        url = 'https://api.moltin.com/v2/carts'
        headers = {
            'Authorization': self.get_token()['access_token'],
            'x-moltin-customer-token': customer_token
        }
        response = requests.post(url, json={'data': {'name': 'Cart'}}, headers=headers)
        check_response(response)
        return response.json()

    def add_product_to_cart(self, product_id: str, quantity: int, cart_ref: str, customer_token: str):
        url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
        headers = {
            'Authorization': self.get_token()['access_token'],
            'x-moltin-customer-token': customer_token
        }
        payload = {'data': {
            'quantity': quantity,
            'type': 'cart_item',
            'id': product_id
        }}
        response = requests.post(url, json=payload, headers=headers)
        check_response(response)
        return response.json()


def check_response(response: requests.Response):
    if 'errors' in response.text:
        raise requests.exceptions.HTTPError(response.text)
    response.raise_for_status()
