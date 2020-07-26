from mongoengine import connect
from mongoengine.connection import disconnect
from credentials import DB_URI
import db_models
from datetime import datetime
import logging
import sys

# Enable logging
logging.basicConfig(filename="logs",
                        stream=sys.stdout,
                        filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

logger = logging.getLogger(__name__)


# Connect to, return database
def db_connect(database):
    db = connect(database, host=DB_URI)
    return db


def add_item(dict):
    item = db_models.Item(**dict)
    item.save()


def add_item_variant(item_variant_dict, context):
    chat_id = context.chat_data["chat_id"]
    chart_id = context.chat_data["chart_id"]
    # index = context.chat_data['chosen_variant_index']
    # item_variant_dict = context.chat_data["variants"][index]

    if item_variant_dict['channel'] == 'shopee':
        # if variant does not exist, create variant
        if db_models.ItemVariant.objects(variant_id=item_variant_dict['variant_id']).count() == 0:
            item_variant_dict['last_updated_time'] = datetime.now()
            # create new lists
            item_variant_dict['chat_ids'] = [chat_id]
            item_variant_dict['chart_ids'] = [chart_id]
            item_variant_dict['price_history'] = [add_price(item_variant_dict)]
            item_variant_dict['created_price'] = item_variant_dict['current_price']
            # add creation time
            item_variant_dict['created_time'] = datetime.now()
            item_variant_dict['item_url'] = context.chat_data["item_url"]

            item_variant = db_models.ItemVariant(**item_variant_dict)
            item_variant.save()
            logger.info(f"Bot saved new item variant in DB: {item_variant_dict['variant_id']}")
        # if variant exists, add chat id
        else:
            # update fields
            item_variant_dict['last_updated_time'] = datetime.now()

            # current_price = decimal.Decimal(item_variant_dict['current_price'])
            # calculate price change since first entry
            # first_price = db_models.ItemVariant.objects.get(item_id=item_variant_dict['item_id'])['price_list'][0]
            # price_change = last_price - first_price
            # price_change_percent = price_change / first_price
            db_models.ItemVariant.objects(_id=item_variant_dict['variant_id']).update_one(add_to_set__chat_ids=chat_id,
                                                                                              add_to_set__chart_ids=chart_id,
                                                                                                set__last_updated_time=datetime.now(),
                                                                                                upsert=True
                                                                                           # push__price_list=last_price,
                                                                                           # set__price_change=price_change,
                                                                                           # set__price_change_percent=price_change_percent
                                                                                           )
            logger.info(f"Bot updated item variant in DB: {item_variant_dict['variant_id']}")


def add_chat(context):
    chat_id = str(context.chat_data['chat_id'])
    user = context.chat_data['user']
    chat_chart = add_chart(context)
    db_models.Chat.objects(chat_id=chat_id).upsert_one(set__chat_id=chat_id,
                                                       set__chat_created_time=datetime.now(),
                                                       set__user_id=str(user['id']),
                                                       set__user_first_name=user['first_name'],
                                                       set__username=user['username'],
                                                       push__chart_messages=chat_chart
                                                       )


def add_chart(context):
    # Find message_id
    chart_id = context.chat_data["chart_id"]
    chat_id = str(context.chat_data['chat_id'])
    chart_name = context.chat_data['chart_name']

    variant_ids = [i['variant_id'] for i in context.chat_data['chosen_variants']]
    # Store fields in dict
    chat_chart_dict = {
        'chat_id': chat_id,
        'chart_id': chart_id,
        'threshold': context.chat_data['threshold'],
        'variants': variant_ids,
        'chart_name': chart_name,
    }
    chat_chart = db_models.ChatChartMessage(**chat_chart_dict)

    chart_variants = []
    chart_variant_names = []
    for i in context.chat_data['chosen_variants']:
        chart_variants.append(add_chart_variant(i, context))
        # variant_id = i['variant_id']
        variant_name = i['variant_name']
        item_name = i['item_name']
        chart_variant_name = item_name + " " + variant_name
        chart_variant_names.append(chart_variant_name)
    # Find variant ids
    # index = context.chat_data['chosen_variant_index']
    # item_variant_dict = context.chat_data["variants"][index]

    # Store fields in dict
    chart_dict = {
        'chat_id': chat_id,
        'chart_id': chart_id,
        'threshold': context.chat_data['threshold'],
        'variants': chart_variants,
        'variant_names': chart_variant_names,
        'chart_name': chart_name,
        'notified_count': 0
    }

    chart = db_models.Chart(**chart_dict)
    chart.save()
    logger.info("DB: Chart stored")

    return chat_chart


def add_chart_variant(item_variant_dict, context):
    # index = context.chat_data['chosen_variant_index']
    # item_variant_dict = context.chat_data["variants"][index]
    variant_id = item_variant_dict['variant_id']
    variant_name = item_variant_dict['variant_name']
    item_name = item_variant_dict['item_name']
    channel = context.chat_data['channel']
    current_price = item_variant_dict['current_price']
    created_price = item_variant_dict['current_price']
    item_url = item_variant_dict['item_url']

    created_time = datetime.now()
    last_updated_time = datetime.now()

    # add into dict
    chart_variant_dict = {
        'variant_id': variant_id,
        'variant_name': variant_name,
        'item_name': item_name,
        'channel': channel,
        'created_time': created_time,
        'last_updated_time': last_updated_time,
        'current_price': current_price,
        'created_price': created_price,
        'item_url': item_url
    }
    chart_variant = db_models.ChartVariant(**chart_variant_dict)
    logger.info("add_chart_variant: Created chart variant")
    return chart_variant


# def add_price(context):
#     index = context.chat_data['chosen_variant_index']
#     price_dict = {
#         'price': context.chat_data["variants"][index]['current_price'],
#         'date': datetime.now()
#     }
#     price = db_models.Price(**price_dict)
#     logger.info("add_price: Created price")
#     return price

def add_price(item_variant_dict):
    # index = context.chat_data['chosen_variant_index']
    price_dict = {
        'price': item_variant_dict['current_price'],
        'date': datetime.now()
    }
    price = db_models.Price(**price_dict)
    logger.info("add_price: Created price")
    return price


def store_in_db(context):
    # Store in db chat, chart, chart variant
    logger.info(f"DB: Starting DB operations...")
    for i in context.chat_data['items']:
        add_item(i)
        logger.info(f"DB: Item stored: {i['item_name']} ")
    for j in context.chat_data['chosen_variants']:
        add_item_variant(j, context)
        logger.info(f"DB: Item Variant stored: {j['variant_name']}")
    add_chat(context)
    logger.info(f"DB: Chat stored")
    logger.info(f"DB: Completed DB operation.")


def retrieve_chart_collection():
    charts = db_models.Chart.objects
    logger.info(f"{len(charts)} charts to update...")
    return charts


def retrieve_charts_to_notify():
    charts = db_models.Chart.objects(threshold_hit=1, notified_count__lt=3)
    logger.info(f"{len(charts)} notifications to send...")
    return charts


def increment_notified_count(chat_id, chart_id):
    db_models.Chart.objects(chat_id=chat_id, chart_id=chart_id).update_one(inc__notified_count=1,
                                                                           upsert=True)
    logger.info(f"Incremented notified count for chat {chat_id} chart {chart_id}")
