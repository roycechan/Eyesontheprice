
import logging
from credentials import TELEGRAM_TOKEN
from telegram.ext import Updater
import telegram.ext
import db_utils
import plotly_utils
import utils
import sys


# Enable logging
logging.basicConfig(filename="logs",
                        filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

logger = logging.getLogger(__name__)

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def update_charts():
    """
    Update stored charts and send them to each user
    """
    logger.info(f"Starting update_charts...")
    logger.info(f"Retrieving chart collection objects...")
    charts = db_utils.retrieve_chart_collection()
    logger.info(f"Retrieved chart collection objects")
    for chart in charts:
        if chart.chart_name is not None:
            chart_name = chart.chart_name
        else:
            chart_name = "Price Change"
        image_url, labels, current_prices, price_changes, created_dates = plotly_utils.update_image(chart.chat_id, chart.chart_id, chart_name)
        logger.info(f"Stored chart {chart_name} {chart.chart_id} for {chart.chat_id}")
        if image_url is not None:
            send_chart_to_user(chart.chat_id, chart.chart_id, image_url, labels, current_prices, price_changes, created_dates)
    logger.info(f"Update complete\n\n-----\n\n")


def send_chart_to_user(chat_id, message_id, image_url, labels, current_prices, price_changes, created_dates):
    """
    :param chat_id: telegram chat_id
    :param message_id: telegram message_id
    :param image_url: url of stored chart
    """
    current_date = utils.get_current_date()

    caption = f"Price changes since _{created_dates[0]}_:\n\n"
    for i, label in enumerate(labels):
        caption += f"{label}: ${current_prices[i]} *({price_changes[i]:.1f}%)*\n"
    caption += f"\n_Last updated on {current_date}_"

    chart = open(image_url, "rb")
    try:
        bot.editMessageMedia(chat_id=chat_id,
                             message_id=message_id,
                             media=telegram.InputMediaPhoto(chart,
                                                            caption=caption,
                                                            parse_mode='Markdown'
                                                            )
                             )
        logger.info(f"Updated chart {message_id} for {chat_id}")
    except telegram.error.BadRequest:
        logger.info(f"Already updated chart {message_id} for {chat_id}, skipping...")


# todo: send notifications if price drops below threshold
def send_notification_to_user():
    logger.info(f"Starting user notification...")
    logger.info(f"Retrieving chart collection objects...")
    charts = db_utils.retrieve_charts_to_notify()
    logger.info(f"Retrieved chart collection objects")
    text = ""
    for chart in charts:
        count = 0
        for variant in chart.variants:
            if variant.price_change_percent < chart.threshold:
                text += f"Woohoo!\n\nItem: {variant.item_name}\nSub-product: {variant.variant_name}\n"
                text += f"*Current Price: ${variant.current_price} ({variant.price_change_percent:.1f}%)*"
                text += f"\n\n[BUY IT NOW ON {variant.channel.upper()}]({variant.item_url})"
                bot.send_message(chat_id=chart.chat_id, text=text, parse_mode="Markdown")
                logger.info(f"Sent notification to user for chat {chart.chat_id} chart {chart.chart_id} variant {variant.variant_name}")
                count += 1
            else:
                logger.info(f"No update for chat {chart.chat_id} chart {chart.chart_id} variant {variant.variant_name}")
        if count > 0:
            db_utils.increment_notified_count(chart.chat_id, chart.chart_id)
    logger.info(f"User notification done.\n\n-----\n\n")

def callback_30(context: telegram.ext.CallbackContext):
    context.bot.send_message(chat_id=429954679,
                             text='A single message with 30s delay')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    j = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # log all errors
    dp.add_error_handler(error)

    # j.run_once(callback_30, 30)
    # run tasks
    update_charts()
    send_notification_to_user()

    # Start the Bot
    # updater.start_polling()

if __name__ == '__main__':
    db = db_utils.db_connect("eyesontheprice")
    main()

