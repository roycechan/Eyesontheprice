from mongoengine import connect
from mongoengine.connection import disconnect
from credentials import DB_URI
import db_models
from datetime import datetime
import logging
import decimal

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to, return database
def db_connect(database):
    db = connect(database, host=DB_URI)
    return db

def add_item(dict):
    item = db_models.Item(**dict)
    item.save()


def add_item_variant(context):
    chat_id = context.chat_data["chat_id"]
    index = context.chat_data['chosen_variant_index']
    item_variant_dict = context.chat_data["variants"][index]

    if item_variant_dict['channel'] == 'shopee':
        # check if item_variant already exists
        if db_models.ItemVariant.objects(item_id=item_variant_dict['item_id']).count() == 0:
            # create new lists
            item_variant_dict['chat_ids'] = [chat_id]
            item_variant_dict['price_list'] = [item_variant_dict['last_updated_price']]
            # add creation time
            item_variant_dict['created_time'] = datetime.now()
            item_variant = db_models.ItemVariant(**item_variant_dict)
            item_variant.save()
            logger.info(f"New item variant saved: {item_variant_dict['item_id']}")
        else:
            # update fields
            item_variant_dict['last_updated_time'] = datetime.now()
            last_price = decimal.Decimal(item_variant_dict['last_updated_price'])
            # calculate price change since first entry
            # first_price = db_models.ItemVariant.objects.get(item_id=item_variant_dict['item_id'])['price_list'][0]
            # price_change = last_price - first_price
            # price_change_percent = price_change / first_price
            db_models.ItemVariant.objects(item_id=item_variant_dict['item_id']).update_one(add_to_set__chat_ids=chat_id,
                                                                                           set__last_updated_time=datetime.now()
                                                                                           # push__price_list=last_price,
                                                                                           # set__price_change=price_change,
                                                                                           # set__price_change_percent=price_change_percent
                                                                                           )
            logger.info(f"Item variant updated: {item_variant_dict['item_id']}")