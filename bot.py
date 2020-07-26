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
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

logger = logging.getLogger(__name__)

INITIAL_CHOICE, CHOOSE_THRESHOLD, CHOOSE_VARIANT, STORE_THRESHOLD, ADD_PRODUCT_CHOICE,TYPE_CHART_NAME, STORE_SUGGESTION = range(7)

SUPPORTED_CHANNELS = ['shopee']

start_reply_keyboard = [['Start tracking prices']]

returning_reply_keyboard = [['Track price of new product',
                             'Add product to existing chart',
                             'Remove product from existing chart',
                             'Remove existing chart']]

threshold_reply_keyboard = ['When price drops by more than 10%',
                            'When price drops by more than 20%',
                            'When price drops by more than 30%',
                            "Don't need to update me"]

add_product_existing_reply_keyboard = ['Add a similar product',
                                       'No other products to add']


def start(update, context):
    # First time user flow
    update.message.reply_text(
        "Hi! I keep my eyes on the price so you don't have to. \n\n I make it easy for you to compare and track prices of similar products across platforms.\n"
        "Currently, I support Shopee. I will support Lazada and Qoo10 in the coming months\n\n"
        'Send /cancel to stop talking to me.\n\n'
        'What can I do for you today?',
        reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
    return INITIAL_CHOICE


def compare(update, context):
    return INITIAL_CHOICE


def track(update, context):
    return INITIAL_CHOICE


def prompt_url(update, context):
    # store char id and user data
    context_store_chat_id(update, context)
    context_store_user(update, context)

    logger.info(f"{context.chat_data['user'].first_name} chose {update.message.text}")
    update.message.reply_text('All right! Please paste a Shopee product URL here.',
                              reply_markup=ReplyKeyboardRemove())

    return CHOOSE_VARIANT


def get_url_and_display_variant(update, context):
    user = context.chat_data['user']

    search_url = utils.extract_url(update, context)
    if search_url is not None:
        logger.info("Bot extracted URL: %s", search_url)
        channel = utils.extract_domain(search_url)
        if channel in SUPPORTED_CHANNELS:
            update.message.reply_text(f"I support {channel}. Brb! I'm going to find out more about the product.")
            item_dict, variants_dict, variants_display_dict = utils.get_item_information(channel, search_url)
            update.message.reply_markdown(f'Hurray! We found \n\n`{item_dict["item_name"]}`\n\n'
                                          'Which sub-product prices would you like to track?',
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

    update.message.reply_text(f'I will create a chart for you to track the prices over time. \n\nBefore I do so, would you like to add a similar product to track in this chart e.g. another listing on Shopee that is similar to your product?',
                              reply_markup=ReplyKeyboardMarkup.from_column(add_product_existing_reply_keyboard,
                                                                           one_time_keyboard=True))
    return ADD_PRODUCT_CHOICE


def get_chart_name(update, context):
    user = context.chat_data['user']
    update.message.reply_text(f"Now, it's time to give your chart a name!")
    logger.info(f"BOT: prompted {user.first_name} for chart name")

    return TYPE_CHART_NAME


def display_threshold(update, context):
    user = context.chat_data['user']

    text = update.message.text
    context.chat_data['chart_name'] = text
    logger.info("Chart name: " + text)

    update.message.reply_text(f'Would you like to receive updates when the price drops?',
                              reply_markup=ReplyKeyboardMarkup.from_column(threshold_reply_keyboard,
                                                                           one_time_keyboard=True))

    logger.info(f"BOT: prompted {user.first_name} for notification threshold")
    return STORE_THRESHOLD


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

    update.message.reply_markdown(message)
    logger.info("BOT: sent tracking summary")

    # todo send tracking summary message
    # send_tracking_summary(update,context)
    send_first_graph(update, context)

    # Store in context
    context.chat_data['threshold'] = parsed_threshold
    logger.info(f"CONTEXT: stored threshold:{parsed_threshold}")

    # Store everything in DB
    db_utils.store_in_db(context)

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
    update.message.reply_markdown("Do you have suggestions on how we can improve the bot, or ideas on which new websites to track?\n\n"
                                  "Leave a comment for us and we'll get cracking ;)",
                                  reply_markup=ReplyKeyboardRemove())
    return STORE_SUGGESTION


def store_suggestion(update, context):
    context.chat_data['suggestion'] = update.message.text
    update.message.reply_markdown("Thank you for your suggestion.")
    # Store everything in DB
    db_utils.store_in_db_suggestion(context)
    return cancel


def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text("Bye for now! We'll continue keeping an eye on your prices.",
                              reply_markup=ReplyKeyboardRemove())

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
                      CommandHandler('cancel', cancel)
                      ],

        states={

            INITIAL_CHOICE: [MessageHandler(Filters.text, prompt_url),
                             ],

            CHOOSE_VARIANT: [MessageHandler(Filters.all, get_url_and_display_variant)],

            CHOOSE_THRESHOLD: [MessageHandler(Filters.text, get_variants)
                               ],

            STORE_THRESHOLD: [MessageHandler(Filters.text, get_threshold_and_send_graph)],

            ADD_PRODUCT_CHOICE: [MessageHandler(Filters.regex('^Add a similar product$'), prompt_url),
                                 MessageHandler(Filters.regex('^No other products to add$'), get_chart_name)],

            TYPE_CHART_NAME: [MessageHandler(Filters.text, display_threshold)],

            STORE_SUGGESTION: [MessageHandler(Filters.text, store_suggestion)],

        },

        fallbacks=[CommandHandler('cancel', cancel)],

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