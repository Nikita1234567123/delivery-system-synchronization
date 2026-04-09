from flask import Flask, render_template, request, jsonify
from datetime import datetime
import time
import threading

app = Flask(__name__)
app.secret_key = 'secret-key-2026'

# Хранилище заказов
orders = {}
next_order_id = 1

# Состояние синхронизации (по умолчанию ВЫКЛЮЧЕНА, чтобы показать проблему)
sync_enabled = False


class Order:
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.status = 'pending'  # pending, taken
        self.taken_by = []  # список курьеров, которые взяли заказ (для демонстрации конфликта)
        self.created_at = datetime.now().strftime('%H:%M:%S')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dispatcher')
def dispatcher():
    return render_template('dispatcher.html', orders=orders, sync_enabled=sync_enabled)


@app.route('/courier/<int:courier_id>')
def courier(courier_id):
    couriers = {1: 'Алиса', 2: 'Борис'}
    return render_template('courier.html', courier_id=courier_id, courier_name=couriers.get(courier_id, 'Курьер'))


@app.route('/api/get_orders')
def get_orders():
    orders_data = {}
    for order_id, order in orders.items():
        orders_data[order_id] = {
            'id': order.id,
            'description': order.description,
            'status': order.status,
            'taken_by': order.taken_by,
            'created_at': order.created_at
        }
    return jsonify({'orders': orders_data})


@app.route('/api/create_order', methods=['POST'])
def create_order():
    global next_order_id
    data = request.get_json()
    description = data.get('description', f'Заказ #{next_order_id}')

    order = Order(next_order_id, description)
    orders[next_order_id] = order
    next_order_id += 1

    return jsonify({'success': True, 'order_id': order.id})


@app.route('/api/take_order', methods=['POST'])
def take_order():
    global orders
    data = request.get_json()
    order_id = data.get('order_id')
    courier_id = data.get('courier_id')

    couriers = {1: 'Алиса', 2: 'Борис'}
    courier_name = couriers.get(courier_id, f'Курьер {courier_id}')

    order = orders.get(order_id)

    if not order:
        return jsonify({'success': False, 'error': 'Заказ не найден'})

    # Искусственная задержка 1.5 секунды, чтобы создать окно для конфликта
    time.sleep(1.5)

    # РЕЖИМ БЕЗ СИНХРОНИЗАЦИИ (sync_enabled = False)
    if not sync_enabled:
        # Проблема: заказ могут взять несколько курьеров!
        order.taken_by.append(courier_id)

        # Если заказ взяли хотя бы один раз - меняем статус
        if len(order.taken_by) == 1:
            order.status = 'taken'

        # Сообщаем результат
        if len(order.taken_by) == 1:
            return jsonify(
                {'success': True, 'message': f'✅ Заказ #{order_id} взят курьером {courier_name}', 'conflict': False})
        else:
            return jsonify({'success': True,
                            'message': f'⚠️ Заказ #{order_id} ТОЖЕ взят курьером {courier_name} (КОНФЛИКТ! Заказ уже взял {", ".join([couriers.get(c, str(c)) for c in order.taken_by if c != courier_id])})',
                            'conflict': True})

    # РЕЖИМ С СИНХРОНИЗАЦИЕЙ (sync_enabled = True)
    else:
        if order.status != 'pending':
            return jsonify({'success': False,
                            'error': f'❌ Заказ #{order_id} уже взят курьером {couriers.get(order.taken_by[0], order.taken_by[0]) if order.taken_by else "неизвестным"}'})

        order.taken_by.append(courier_id)
        order.status = 'taken'
        return jsonify(
            {'success': True, 'message': f'✅ Заказ #{order_id} взят курьером {courier_name}', 'conflict': False})


@app.route('/api/toggle_sync', methods=['POST'])
def toggle_sync():
    global sync_enabled
    data = request.get_json()
    sync_enabled = data.get('enabled', False)
    return jsonify({'success': True, 'sync_enabled': sync_enabled})


@app.route('/api/get_sync_status')
def get_sync_status():
    global sync_enabled
    return jsonify({'sync_enabled': sync_enabled})


@app.route('/api/reset', methods=['POST'])
def reset():
    global orders, next_order_id, sync_enabled
    orders = {}
    next_order_id = 1
    sync_enabled = False
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)