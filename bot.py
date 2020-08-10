#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import plotly_utils
import utils, db_utils, shopee_utils
import logging
from credentials import TELEGRAM_TOKEN
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
import telegram
from datetime import datetime
import os
import shutil
import sys


bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Enable logging
logging.basicConfig(filename="logs",
                        filemode='a',
                        format='%(asctime)s - %(module)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

logger = logging.getLogger(__name__)

INITIAL_CHOICE, \
CHOOSE_THRESHOLD, \
CHOOSE_VARIANT, \
STORE_THRESHOLD, \
ADD_PRODUCT_CHOICE,\
TYPE_CHART_NAME, \
STORE_SUGGESTION, \
CHART_COMMANDS, \
DISPLAY_CHARTS, \
FIND_CHART, \
DELETE_CHART \
    = range(11)

SUPPORTED_CHANNELS = ['shopee']

start_reply_keyboard = [["Let's go!"]]

returning_reply_keyboard = [['Track price of new product',
                             'Add product to existing chart',
                             'Remove product from existing chart',
                             'Remove existing chart']]

threshold_reply_keyboard = ['When price drops by more than 10%',
                            'When price drops by more than 20%',
                            'When price drops by more than 30%',
                            "I don't need an update"]

add_product_existing_reply_keyboard = ["I'll like to add this product",
                                       "I don't have another product to add"]

chart_reply_keyboard = ['Find chart',
                        'Delete chart',
                        'Add product into existing chart',
                        'Delete product from existing chart'
                        ]


def start(update, context):
    context_clear(context)
    # First time user flow
    update.message.reply_text(
        "Hi! I've my eyes glued to the prices so you don't have to. \n\n"
        "I make it easy for you to compare and track prices of similar products across platforms, just give me a clue.\n\n"
        "Currently, I can help you with Shopee. Give me a couple of weeks while I learn about Lazada and Qoo10, whee!\n\n"
        "Let the tracking begin!",
        reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
    return INITIAL_CHOICE


def compare(update, context):
    return INITIAL_CHOICE


def track(update, context):
    return INITIAL_CHOICE


def prompt_next_url(update, context):
    # store char id and user data
    context_store_chat_id(update, context)
    context_store_user(update, context)

    logger.info(f"{context.chat_data['user'].first_name} chose {update.message.text}")
    update.message.reply_text('Tell me, what might your Shopee product URL be?',
                              reply_markup=ReplyKeyboardRemove())

    return CHOOSE_VARIANT


def prompt_url(update, context):
    context_clear(context)
    # store char id and user data
    context_store_chat_id(update, context)
    context_store_user(update, context)

    logger.info(f"{context.chat_data['user'].first_name} chose {update.message.text}")
    update.message.reply_text('Tell me, what might your Shopee product URL be?',
                              reply_markup=ReplyKeyboardRemove())

    return CHOOSE_VARIANT


def get_url_and_display_variant(update, context):
    user = context.chat_data['user']

    search_url = utils.extract_url(update, context)
    if search_url is not None:
        logger.info("Bot extracted URL: %s", search_url)
        channel = utils.extract_domain(search_url)
        if channel in SUPPORTED_CHANNELS:
            update.message.reply_text(f"Brb! I'm learning more about this product on {channel}.")
            item_dict, variants_dict, variants_display_dict = utils.get_item_information(channel, search_url)
            update.message.reply_markdown(f"Hurray! Ive found \n\n{item_dict['item_name']}\n\n"
                                          'Which of these product variations would you like to track?',
                                          reply_markup=ReplyKeyboardMarkup.from_column(variants_display_dict,
                                                                                       one_time_keyboard=True))
            logger.info(f"BOT: prompted {user.first_name} for variant choice")

            # Store in context
            context_store_item(item_dict, context)
            context.chat_data['item_url'] = utils.shorten_url([search_url])[0]
            context.chat_data['channel'] = utils.extract_domain(search_url)
            context.chat_data['variants'] = variants_dict
            logger.info(context.chat_data['variants'])
            context.chat_data['variants_displayed'] = variants_display_dict
            # context.chat_data['item'] = item_dict
            logger.info(f"CONTEXT: Stored channel, variants, display, url for item {item_dict['item_name']}")

            return CHOOSE_THRESHOLD

        else:
            update.message.reply_text(f"Oops, I do not support {channel} yet. Let's try again.",
                                      reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
            return INITIAL_CHOICE
    else:
        update.message.reply_text("Oops, you did not key in a valid URL. Let's try again.",
                                  reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
        return INITIAL_CHOICE


def get_variants(update, context):
    user = context.chat_data['user']
    chosen_variant = update.message.text
    variants_displayed = context.chat_data['variants_displayed']

    chosen_variant_index = variants_displayed.index(chosen_variant)
    logger.info(f"{user.first_name} chose {chosen_variant}")

    # Store in context
    context.chat_data['variants'][chosen_variant_index]['item_url'] = context.chat_data['item_url']
    context_store_item_variant(context.chat_data['variants'][chosen_variant_index], context)
    context.chat_data['chosen_variant'] = chosen_variant
    context.chat_data['chosen_variant_index'] = chosen_variant_index
    logger.info(f"CONTEXT: chosen variant: {chosen_variant}, index: {chosen_variant_index}")

    update.message.reply_text(f"I'll chart out the prices across time to help you with price tracking! \n\n"
                              f"Is there a similar product you'll like to add to the chart? e.g. a similar product on {context.chat_data['channel']}?",
                              reply_markup=ReplyKeyboardMarkup.from_column(add_product_existing_reply_keyboard,
                                                                           one_time_keyboard=True))
    return ADD_PRODUCT_CHOICE


def get_chart_name(update, context):
    user = context.chat_data['user']
    update.message.reply_text(f"Now, it's time to give your chart a name!\n\n" 
                               "You can retrieve this chart through its name next time!")
    logger.info(f"BOT: prompted {user.first_name} for chart name")

    return TYPE_CHART_NAME


def display_threshold(update, context):
    user = context.chat_data['user']
    chat_id = str(update.message.chat.id)
    text = update.message.text

    if db_utils.validate_chart_name(chat_id, text) is False:
        logger.info(f"BOT: {user.first_name}'s chart name is unused")
        context.chat_data['chart_name'] = text
        logger.info("Chart name: " + text)

        update.message.reply_text(f'Shall I send you an alert when the price drops?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(threshold_reply_keyboard,
                                                                               one_time_keyboard=True))

        logger.info(f"BOT: prompted {user.first_name} for notification threshold")
        return STORE_THRESHOLD
    else:
        logger.info(f"BOT: {user.first_name}'s chart name is used, prompting user for another chart name")
        update.message.reply_text(f"Oops! You've used this chart name before. Please give your chart another name!")
        return get_chart_name(update, context)


def get_threshold_and_send_graph(update, context):
    user = context.chat_data['user']
    chosen_threshold = update.message.text
    logger.info(f"{user.first_name} chose {chosen_threshold}")
    parsed_threshold = utils.parse_threshold(chosen_threshold)

    # todo set callback details
    # todo: add reply for other variants

    message = "Great! You've chosen to track the following: \n\n"
    number = 1
    for i in context.chat_data['chosen_variants']:
        message += f"{number}. {i['item_name']} - {i['variant_name']} \n\n"
        number += 1
    message += f"Notification: {chosen_threshold}\n\n"
    # message += f"We'll update the chart daily. Check back again tomorrow :)"

    update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    logger.info("BOT: sent tracking summary")

    # todo send tracking summary message
    # send_tracking_summary(update,context)
    send_first_graph(update, context)

    # Store in context
    context.chat_data['threshold'] = parsed_threshold
    logger.info(f"CONTEXT: stored threshold:{parsed_threshold}")

    # Store everything in DB
    db_utils.store_in_db(context)
    context_clear(context)

    return ConversationHandler.END


def send_first_graph(update, context):
    index = context.chat_data['chosen_variant_index']
    item_variant = context.chat_data["variants"][index]
    current_price = item_variant['current_price']
    variant_id = item_variant['variant_id']
    chat_id = str(update.message.chat.id)

    # Create image
    photo_url = plotly_utils.generate_photo_url(update,context)
    # update.message.reply_photo(photo=open("images/fig1.png", "rb"))
    photo = open(photo_url, "rb")
    updated_date = utils.get_current_date()
    message = bot.send_photo(chat_id=update.message.chat.id,
                   photo=photo,
                   parse_mode='Markdown',
                   caption=f"_Last updated on {updated_date}_")

    chart_id = str(message.message_id)
    perm_save_url = f"{plotly_utils.IMAGE_DESTINATION}{chat_id}_{chart_id}.png"
    # Update photo url with message id
    photo.close()
    if photo_url is not plotly_utils.SAMPLE_IMAGE_URL:
        shutil.move(photo_url, perm_save_url)

    # Store in context
    context.chat_data['chart_id'] = chart_id
    logger.info("BOT: sent first chart.")


def get_suggestion(update, context):
    context_store_user(update, context)
    update.message.reply_markdown("Do you have suggestions on how we can improve the bot, or ideas on new websites to track?\n\n"
                                  "Leave a comment and we'll get cracking ;)",
                                  reply_markup=ReplyKeyboardRemove())
    return STORE_SUGGESTION


def store_suggestion(update, context):
    context.chat_data['suggestion'] = update.message.text
    update.message.reply_markdown("Thanks for your suggestion.")
    # Store everything in DB
    db_utils.store_in_db_suggestion(context)
    return ConversationHandler.END


def chart(update, context):
    logger.info(f"BOT: User requesting chart information")
    update.message.reply_text(f"Finding a chart that you previously saved? Need to add a new chart?",
                              reply_markup=ReplyKeyboardMarkup.from_column(chart_reply_keyboard,
                                                                           one_time_keyboard=True))
    return CHART_COMMANDS


def display_charts(update, context):
    chart_choice = update.message.text
    chat_id = str(update.message.chat.id)
    chart_names = db_utils.get_chart_names(chat_id)
    update.message.reply_text(f"Which chart would you like to retrieve or edit?",
                              reply_markup=ReplyKeyboardMarkup.from_column(chart_names,
                                                                           one_time_keyboard=True))

    if "Find chart" in chart_choice:
        return FIND_CHART
    elif "Delete chart" in chart_choice:
        return DELETE_CHART
    #
    # ndler(Filters.regex("^Find chart$|^Delete chart$"), display_charts),
    # MessageHandler(Filters.regex("^Add chart$"), add_chart),
    # MessageHandler(Filters.regex("^Add product into existing chart$"), display_charts),
    # MessageHandler(Filters.regex("^Delete product from existing chart$"), display_charts),


def find_chart(update, context):
    chart_name = update.message.text
    chat_id = str(update.message.chat.id)
    user = update.message.from_user
    logger.info(f"{user.first_name} is finding {chart_name}")
    chart_id = db_utils.get_chart_id(chat_id, chart_name)
    logger.info(f"DB: Found {user.first_name}'s {chart_name} message {chart_id}")
    return chat_id, chart_id


def retrieve_chart(update, context):
    chat_id, chart_id = find_chart(update, context)
    bot.send_message(chat_id=chat_id,
                     text=f"Found it! Jump to your chart by clicking on the message above",
                     reply_to_message_id=chart_id,
                     reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def delete_chart(update, context):
    chat_id, chart_id = find_chart(update, context)
    db_utils.delete_chart(chat_id, chart_id)
    bot.send_message(chat_id=chat_id,
                     text=f"Found it! We've stopped tracking this chart.",
                     reply_to_message_id=chart_id,
                     reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def add_chart(update, context):
    return prompt_url()


def add_product_chart(update, context):
    return None


def delete_product_chart(update, context):
    return None


def end(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text("Bye for now! Leave it to me, I'll keep an eye on the prices you wanna track.",
                              reply_markup=ReplyKeyboardRemove())
    context_clear(context)
    print(context.chat_data)
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# CONTEXT UTILS
def context_store_chat_id(update, context):
    context.chat_data['chat_id'] = str(update.message.chat.id)
    logger.info(f"CONTEXT: Stored chat_id: {context.chat_data['chat_id']}")


def context_store_user(update, context):
    context.chat_data['user'] = update.message.from_user
    logger.info(f"CONTEXT: Stored user: {context.chat_data['user']}")


def context_store_item(item_dict, context):
    if 'items' in context.chat_data.keys():
        context.chat_data['items'].append(item_dict.copy())
    else:
        context.chat_data['items'] = [item_dict]
    item_names = [i['item_name'] for i in context.chat_data['items']]
    # logger.info(context.chat_data)
    logger.info(f"CONTEXT: Stored items: {item_names}")


def context_store_item_variant(item_variant_dict, context):
    if 'chosen_variants' in context.chat_data.keys():
        context.chat_data['chosen_variants'].append(item_variant_dict.copy())
    else:
        context.chat_data['chosen_variants'] = [item_variant_dict]
    logger.info(context.chat_data['chosen_variants'])
    logger.info(f"CONTEXT: Stored variants")


def context_clear(context):
    entries_to_remove = ('item_url',
                         'channel',
                         'variants',
                         'variants_displayed',
                         'chosen_variant',
                         'chosen_variant_index',
                         'chart_name',
                         'threshold',
                         'chart_id',
                         'chosen_variants',
                         'items'
                         )
    for i in entries_to_remove:
        context.chat_data.pop(i, None)
    logger.info("BOT: Cleared context")
    return context


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                      CommandHandler('track', prompt_url),
                      CommandHandler('suggest', get_suggestion),
                      CommandHandler('end', end),
                      CommandHandler('chart', chart)
                      ],

        states={

            INITIAL_CHOICE: [MessageHandler(Filters.text, prompt_url),
                             ],

            CHOOSE_VARIANT: [MessageHandler(Filters.all, get_url_and_display_variant)],

            CHOOSE_THRESHOLD: [MessageHandler(Filters.text, get_variants)
                               ],

            STORE_THRESHOLD: [MessageHandler(Filters.text, get_threshold_and_send_graph)],

            ADD_PRODUCT_CHOICE: [MessageHandler(Filters.regex("^I'll like to add another product$"), prompt_next_url),
                                 MessageHandler(Filters.regex("^I don't have another product to add$"), get_chart_name)],

            TYPE_CHART_NAME: [MessageHandler(Filters.text, display_threshold)],

            STORE_SUGGESTION: [MessageHandler(Filters.text, store_suggestion)],

            CHART_COMMANDS: [MessageHandler(Filters.regex("^Find chart$|^Delete chart$"), display_charts),
                             MessageHandler(Filters.regex("^Add chart$"), add_chart),
                             MessageHandler(Filters.regex("^Add product into existing chart$"), display_charts),
                             MessageHandler(Filters.regex("^Delete product from existing chart$"), display_charts),
                             ],

            FIND_CHART: [MessageHandler(Filters.text, retrieve_chart)],

            DELETE_CHART: [MessageHandler(Filters.text, delete_chart)],

            DISPLAY_CHARTS: [MessageHandler(Filters.text, get_threshold_and_send_graph)]

        },

        fallbacks=[CommandHandler('end', end)],

        allow_reentry=True
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    db = db_utils.db_connect("eyesontheprice")
    main()