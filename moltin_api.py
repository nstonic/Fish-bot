import requests


def get_all_products(api_token: str) -> dict:
    url = 'https://api.moltin.com/pcm/products'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def get_product(api_token: str, product_id: str) -> dict:
    url = f'https://api.moltin.com/pcm/products/{product_id}'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def get_product_prices(api_token: str, product_id: str) -> dict:
    url = f'https://api.moltin.com/pcm/pricebooks/:id/prices/'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def get_image_relationships(api_token: str, product_id: str) -> dict:
    url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def get_file_url_by_id(api_token: str, file_id: str) -> str:
    url = f'https://api.moltin.com/v2/files/{file_id}'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()['data']['link']['href']


def fetch_image(api_token: str, product_id: str):
    image_id = get_image_relationships(api_token, product_id)['data']['id']
    image_url = get_file_url_by_id(api_token, image_id)
    response = requests.get(image_url)
    check_response(response)
    return response.content


# def set_main_image(api_token: str, product_id: str, image_id: str) -> dict:
#     url = f'https://api.moltin.com/pcm/products/{product_id}/relationships/main_image'
#     headers = {
#         'Authorization': api_token
#     }
#     payload = {
#         'data': {
#             'type': 'file',
#             'id': image_id
#         }
#     }
#     response = requests.post(url, headers=headers, json=payload)
#     check_response(response)
#     return response.json()


def get_token(client_id: str, client_secret: str) -> dict:
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    check_response(response)
    return response.json()


def get_customer_token(api_token: str) -> str:
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
    check_response(response)
    return response.json()['data']['token']


def get_cart(api_token: str, cart_ref: str):
    url = f'https://api.moltin.com/v2/carts/{cart_ref}'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def get_cart_items(api_token: str, cart_ref: str) -> dict:
    url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
    headers = {
        'Authorization': api_token
    }
    response = requests.get(url, headers=headers)
    check_response(response)
    return response.json()


def create_cart(api_token: str, customer_token: str):
    url = 'https://api.moltin.com/v2/carts'
    headers = {
        'Authorization': api_token,
        'x-moltin-customer-token': customer_token
    }
    response = requests.post(url, json={'data': {'name': 'Cart'}}, headers=headers)
    check_response(response)
    return response.json()


def add_product_to_cart(product_id: str, quantity: int, cart_ref: str, api_token: str, customer_token: str):
    url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
    headers = {
        'Authorization': api_token,
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


def make_order(product_id: str, quantity: int, api_token: str):
    customer_token = get_customer_token(api_token)
    cart = create_cart(api_token, customer_token)
    add_product_to_cart(
        product_id=product_id,
        quantity=quantity,
        cart_ref=cart['data']['id'],
        api_token=api_token,
        customer_token=customer_token
    )
    return get_cart_items(api_token, cart['data']['id'])


def check_response(response: requests.Response):
    if 'errors' in response.text:
        raise requests.exceptions.HTTPError(response.json())
    response.raise_for_status()
