#!/usr/bin/env .venv/bin/python -W ignore
from libs.bunq_lib import BunqLib
from libs.share_lib import ShareLib
from db_helper import DbHelper
from threading import Thread
import time

from libs.piggybunq_lib import parse_user_discounts, determine_discount

from flask import Flask, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)


@app.route('/hello-world')
def hello_world():
    return 'Hello World!'


@socketio.on('my event')
def handle_my_custom_event(data):
    emit('my response', data, broadcast=True)


@app.route('/discounts')
def get_discounts():
    return jsonify({
        'discounts': parse_user_discounts('data/discount.csv')
    })


@app.route('/payments')
def get_payments():
    database = DbHelper()
    columns = [c[0] for c in database.get_payments_discounts_columns()]
    return jsonify({
        'payments': [dict(zip(columns, t)) for t in database.get_payments_from_database()]
    })


def refresh_database(bunq, discounts):
    database = DbHelper()
    existing_tx = [tranx[0] for tranx in database.get_payments_from_database()]
    history = bunq.get_all_payment(count=200)
    # for h in history:
    #     if h.description.split("-")[0] != "CASHBACK":
    #         _, dsc = determine_discount(h.description, discounts)
    #         database.add_payment_to_database(h.id_, h.description, h.amount.value, dsc*h.amount.value)
    #         existing_tx.append(h.id_)

    while True:
        new_payments = bunq.get_all_payment(5)
        for np in new_payments:
            if str(np.id_) not in existing_tx and np.description.split("-")[0] != "CASHBACK":
                shop, dsc = determine_discount(np.description, discounts)
                database.add_payment_to_database(np.id_, np.description, np.amount.value, dsc * np.amount.value)
                existing_tx.append(str(np.id_))
                if shop is not None:
                    desc = "{}-{}-{}".format("CASHBACK", shop, dsc)
                    print(desc)
                    bunq.make_request(dsc, desc, "sugardaddy@bunq.com")
        time.sleep(3)
        print("socket emit")
        socketio.emit('NewPayment', {'number': 10}, namespace='/test')


def main():

    all_option = ShareLib.parse_all_option()
    environment_type = ShareLib.determine_environment_type_from_all_option(all_option)

    ShareLib.print_header()

    bunq = BunqLib(environment_type)

    user = bunq.get_current_user()

    discounts = parse_user_discounts("data/discount.csv")

    database = DbHelper()

    Thread(target=refresh_database, args=(bunq, discounts)).start()

    # all_request = bunq.get_all_request(1)
    # ShareLib.print_all_request(all_request)
    #
    # all_card = bunq.get_all_card(1)
    # ShareLib.print_all_card(all_card, all_monetary_account_bank_active)
    #
    # if environment_type is ApiEnvironmentType.SANDBOX:
    #     all_alias = bunq.get_all_user_alias()
    #     ShareLib.print_all_user_alias(all_alias)
    #
    # bunq.update_context()

    app.run(debug=True)

if __name__ == '__main__':
    main()
