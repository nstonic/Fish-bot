def parse_cart(cart: dict) -> str:
    total_cost = 0
    if not cart or not cart['data']:
        products_text = 'Ваша корзина пуста'
    else:
        products = []
        for product in cart['data']:
            name = product['name']
            price = product['unit_price']['amount'] / 100
            quantity = product['quantity']
            cost = price * quantity
            total_cost += cost
            products.append(f'{name} - {quantity}кг\nЦена: {price}₽\nСумма: {cost}₽')
        products_text = '\n\n'.join(products)
    return f'<b>Ваша корзина:</b>\n\n{products_text}\n\n<b>Общая стоимость:</b> {total_cost}₽'
