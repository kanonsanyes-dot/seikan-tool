from models import Customer, Product, ProductProcessStandard

def check_data_quality(order):
    customer_names = {c.customer_name for c in Customer.query.filter_by(is_active=True).all()}
    product_names = {p.product_name for p in Product.query.filter_by(is_active=True).all()}
    standard_names = {s.product_name for s in ProductProcessStandard.query.filter_by(is_active=True).all()}
    if not order.ship_date:
        return "要確認"
    if order.quantity is None or order.quantity <= 0:
        return "要確認"
    if order.customer not in customer_names:
        return "客先未登録"
    if order.product_name not in product_names:
        return "品名未登録"
    if standard_names and order.product_name not in standard_names:
        return "工程標準未登録"
    return "照合OK"

def recheck_all(orders):
    for order in orders:
        order.data_quality = check_data_quality(order)
    return orders
