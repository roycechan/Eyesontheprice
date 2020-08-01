import logging
from credentials import TELEGRAM_TOKEN
import telegram.ext
import db_utils
import db_models
import shopee_utils
import sys
from datetime import timedelta
from datetime import datetime
import utils
import numpy as np
from decimal import Decimal
import pymongo
from mongoengine.errors import OperationError
# Enable logging
logging.basicConfig(
                    filename="logs",
                    filemode='a',
                    format='%(asctime)s - %(module)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    )
logging.getLogger().addHandler(logging.StreamHandler())
logger = logging.getLogger(__name__)

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def get_daily_price_and_stock():
    variants = db_models.ItemVariant.objects()
    logger.info(f"Working on fetching daily information for {len(variants)} variants.\n")
    for i, variant in enumerate(variants):
        db_price = variant.current_price
        logger.info(f"{i+1}. {variant.variant_id}: Found db price {db_price}")
        if variant.channel == "shopee":
            current_price, current_stock = get_shopee_response(variant)
            update_variant_collection(current_price, current_stock, variant, db_price, i)


def get_shopee_response(variant):
    parameters = {
        "itemid": variant.item_id,
        "shopid": variant.shop_id
    }
    search_url = utils.build_search_url(utils.SHOPEE_SEARCH_LINK, parameters)
    item_json = utils.retrieve_item_details_json(search_url)
    variant_id = int(variant.variant_id)
    try:
        # logger.info(f"ITEM {variant_id} {item_json['item']['itemid']} {variant_id == item_json['item']['itemid']}")
        if variant_id == item_json["item"]["itemid"]:
            price = int(item_json['item']['price_min']) / shopee_utils.SHOPEE_PRICE_DENOMINATION
            stock = item_json['item']['stock']
            return round(price,2), stock
        else:
            variants = item_json['item']['models']
            for i in variants:
                # logger.info(f"VARIANT {variant_id} {i['modelid']} {variant_id == i['modelid']}")
                if variant_id == int(i['modelid']):
                    price = int(i['price']) / shopee_utils.SHOPEE_PRICE_DENOMINATION
                    stock = i['stock']
                    return round(price,2), stock
    except TypeError:
        logger.error(f"No item found for {variant.variant_id}")
        return 0, 0


def update_variant_collection(current_price, current_stock, variant, db_price, i):
    date_list = get_date_list(variant.created_time)
    price_list = get_price_list(date_list, variant)
    last_updated_time = datetime.now()

    if abs(current_price - float(db_price)) > 0.01:
        price_list[-1] = current_price
        new_price_history = {
            "date": last_updated_time,
            "price": current_price
        }
        db_models.ItemVariant.objects(variant_id=variant.variant_id).update_one(push__price_history=new_price_history,
                                                                                set__last_updated_time=last_updated_time,
                                                                                set__current_price=current_price,
                                                                                set__stock=current_stock,
                                                                                set__price_list=price_list,
                                                                                set__date_list=date_list,
                                                                                set__lowest_price=min(price_list),
                                                                                upsert=True
                                                                                )
        logger.info(f"{i+1}. {variant.variant_id}: Price changed from {db_price} to {current_price}\n")

    else:
        db_models.ItemVariant.objects(variant_id=variant.variant_id).update_one(
                                                                                set__last_updated_time=last_updated_time,
                                                                                set__stock=current_stock,
                                                                                set__price_list=price_list,
                                                                                set__date_list=date_list,
                                                                                set__lowest_price=min(price_list),
                                                                                upsert=True
                                                                                )
        logger.info(f"{i+1}. {variant.variant_id}: Price unchanged at {db_price}\n")


def get_date_list(created_time):
    day_diff = utils.difference_in_days(datetime.now(), created_time) + 1
    date_list = []
    created_date = created_time.date()
    for i in range(day_diff):
        dte = (created_date+timedelta(days=i)).strftime("%Y-%m-%d")
        date_list.append(dte)
    # print(date_list)
    return date_list


def get_price_list(date_list, variant):
    price_list = np.empty(len(date_list))
    price_list.fill(variant.created_price)
    # logger.info(len(date_list))
    # logger.info(date_list)
    # logger.info(price_list)
    start = 0
    for i in range(len(variant.price_history)-1):
        # logger.info(f"start: {start}, end: {end}")
        end = start + utils.difference_in_days(variant.price_history[i+1].date, variant.price_history[i].date)
        # logger.info(f"start: {start}, end: {end}")
        price_list[start:end] = variant.price_history[i].price
        # logger.info(price_list)
        start = end
    price_list[start:] = variant.price_history[-1].price
    # logger.info(f"\n\n")
    return price_list


def copy_chart_variants():
    variant_collection = db_models.ItemVariant.objects()
    logger.info(f"\nCopying {len(variant_collection)} variants from ItemVariant to ChartVariant.")
    for i, variant in enumerate(variant_collection):
        try:
            logger.info(f"Copying {i+1}. {variant.variant_id} {variant.variant_name}")
            db_models.Chart.objects(variants__variant_id=variant.variant_id).update(set__variants__S__price_history=variant.price_history,
                                                                                        set__variants__S__current_price=variant.current_price,
                                                                                        set__variants__S__price_list=variant.price_list,
                                                                                        set__variants__S__date_list=variant.date_list,
                                                                                        set__variants__S__lowest_price=variant.lowest_price,
                                                                                        set__variants__S__last_updated_time=datetime.now(),
                                                                                   )
        except OperationError:
            logger.info(f"Cannot find variant")
            return None
    logger.info(f"Copied {len(variant_collection)} variants from ItemVariant to ChartVariant.")


def update_chart_variants():
    chart_collection = db_models.Chart.objects()
    for i,chart in enumerate(chart_collection):
        logger.info(f"\nUpdating {i + 1}. {chart.chart_id} {chart.chart_name}")
        threshold = chart.threshold
        threshold_hit = 0
        threshold_hit_list = []
        price_change_percent_list = []

        for j, chart_variant in enumerate(chart.variants):
            logger.info(f"Updating {i+1}.{j+1}. {chart_variant.variant_id} {chart_variant.variant_name}")
            price_change = round(chart_variant.current_price - chart_variant.created_price,2)
            price_change_percent = round(price_change / chart_variant.created_price, 2) * 100

            if (price_change_percent < 0) & (price_change_percent < threshold) & (price_change_percent != -100):
                threshold_hit = 1
                logger.info(f"Updating {i+1}.{j+1}. Threshold hit for {chart_variant.variant_id} {chart_variant.variant_name}. {price_change_percent}|{threshold}")
            else:
                logger.info(f"Updating {i+1}.{j+1}. Threshold not hit for {chart_variant.variant_id} {chart_variant.variant_name}. {price_change_percent}|{threshold}")

            threshold_hit_list.append(threshold_hit)
            price_change_percent_list.append(price_change_percent)

            db_models.Chart.objects(variants__variant_id=chart_variant.variant_id).update(
                                        set__variants__S__price_change=chart_variant.price_change,
                                        set__variants__S__price_change_percent=chart_variant.price_change_percent,
                                        set__variants__S__threshold_hit=threshold_hit,
            )

        if any(hit > 0 for hit in threshold_hit_list):
            threshold_hit = 1
            logger.info(f"Updating {i + 1}. Threshold hit for {chart.chart_id} {chart.chart_name} {threshold_hit_list}")
        else:
            threshold_hit = 0
            logger.info(f"No Update {i + 1}. Threshold not hit for {chart.chart_id} {chart.chart_name} {threshold_hit_list}")

        db_models.Chart.objects(chart_id=chart.chart_id, chat_id=chart.chat_id).update(
            set__price_change_percent_list=price_change_percent_list,
            set__threshold_hit_list=threshold_hit_list,
            set__threshold_hit=threshold_hit
        )


def main():
    logger.info("\n--------------------\n")
    logger.info("Getting daily shopee price and stock")
    get_daily_price_and_stock()
    logger.info("\n--------------------\n")
    logger.info("Copying item variants and pasting into chart variants")
    copy_chart_variants()
    logger.info("\n--------------------\n")
    logger.info("Updating chart variants threshold hit")
    update_chart_variants()
    logger.info("\n--------------------\n")


if __name__ == '__main__':
    db = db_utils.db_connect("eyesontheprice")
    main()
    db.close()
    sys.exit()


