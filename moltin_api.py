from pprint import pprint

import requests
from environs import Env


def get_all_products(api_token: str) -> dict:
    url = 'https://api.moltin.com/pcm/products'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(api_token: str, product_id: str) -> dict:
    url = f'https://api.moltin.com/pcm/products/{product_id}'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_token(client_id: str, client_secret: str) -> dict:
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()


def get_customer_token(api_token: str) -> dict:
    url = 'https://api.moltin.com/v2/customers/tokens'
    headers = {
        'Authorization': api_token
    }
    payload = {'data': {
        'type': 'token',
        'email': 'buba@yandex.ru',
        'password': 'eBTjD9xKqVhAhPA',
        'authentication_mechanism': 'password'
    }}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_cart(api_token: str, cart_ref: str):
    url = f'https://api.moltin.com/v2/carts/:{cart_ref}'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_items(api_token: str, cart_ref: str):
    url = f'https://api.moltin.com/v2/carts/:{cart_ref}/items'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def create_cart(api_token: str, customer_token: str):
    url = 'https://api.moltin.com/v2/carts'
    headers = {
        'Authorization': api_token,
        'x-moltin-customer-token': customer_token
    }
    response = requests.post(url, json={'data': {'name': 'Cart'}}, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(product: dict, quantity: int, cart_ref: dict, api_token: str, customer_token: str):
    url = f'https://api.moltin.com/v2/carts/:{cart_ref}/items'
    headers = {
        'Authorization': api_token,
        'x-moltin-customer-token': customer_token
    }
    payload = {'data': {
        'quantity': quantity,
        'type': 'cart_item',
        'id': product['id']
    }}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    env = Env()
    env.read_env()
    token = get_token(
        client_id=env('CLIENT_ID'),
        client_secret=env('CLIENT_SECRET')
    )['access_token']
    customer_token = get_customer_token(token)['data']['token']
    cart = create_cart(
        api_token=token,
        customer_token=customer_token
    )

    all_products = get_all_products(token)
    add_product_to_cart(
        cart_ref=cart["data"]["id"],
        product=all_products['data'][0],
        quantity=1,
        api_token=token,
        customer_token=customer_token
    )
    pprint(get_cart_items(
        api_token=token,
        cart_ref=cart["data"]["id"]
    ))


if __name__ == '__main__':
    main()
