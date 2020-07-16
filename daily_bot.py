
import logging
from credentials import TELEGRAM_TOKEN
from telegram.ext import Updater
import telegram.ext
import db_utils
import plotly_utils
import utils

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

bot = telegram.Bot(token=TELEGRAM_TOKEN)


def update_charts():
    """
    Update stored charts and send them to each user
    """
    logger.info(f"Retrieving chart collection objects...")
    charts = db_utils.retrieve_chart_collection()
    logger.info(f"Retrieved chart collection objects")
    for chart in charts:
        if chart.chart_name is not None:
            chart_name = chart.chart_name
        else:
            chart_name = "Price Change"
        image_url = plotly_utils.update_image(chart.chat_id, chart.chart_id, chart_name)
        logger.info(f"Stored chart {chart_name} {chart.chart_id} for {chart.chat_id}")
        if image_url is not None:
            send_chart_to_user(chart.chat_id, chart.chart_id, image_url)
    logger.info(f"Update complete")


def send_chart_to_user(chat_id, message_id, image_url):
    """
    :param chat_id: telegram chat_id
    :param message_id: telegram message_id
    :param image_url: url of stored chart
    """
    current_date = utils.get_current_date()
    chart = open(image_url, "rb")
    try:
        bot.editMessageMedia(chat_id=chat_id,
                             message_id=message_id,
                             media=telegram.InputMediaPhoto(chart,
                                                            caption=f"_Last updated on {current_date}_"
                                                            )
                             )
        logger.info(f"Updated chart {message_id} for {chat_id}")
    except telegram.error.BadRequest:
        logger.info(f"Already updated chart {message_id} for {chat_id}, skipping...")


# todo: send notifications if price drops below threshold

# get charts from db filter for notification_count=0 and threshold_hit=1
# for i in charts
# # send message with price drop amount



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

    # Start the Bot
    updater.start_polling()

if __name__ == '__main__':
    db = db_utils.db_connect("eyesontheprice")
    main()

