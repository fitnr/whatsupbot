#!/usr/bin/env python
from __future__ import print_function
import argparse
from datetime import datetime
try:
    import twitter_bot_utils as tbu
except ImportError:
    import tweepy


def last_tweet(api, screen_name):
    '''Hours since last tweet. Returns float/int.'''
    try:
        created_at = api.user_timeline(screen_name, count=1)[0].created_at
        now = datetime.now()

        return (now - created_at).total_seconds() / 3600.

    except (TypeError, IndexError):
        return -1


def notify(api, text, recipient=None):
    if recipient:
        api.send_direct_message(screen_name=recipient, text=text)
    else:
        print(text)


def whatsup(api, screen_name, hours, sender=None, confirm=False):
    elapsed = last_tweet(api, screen_name)
    message = ''

    if elapsed == -1:
        if sender == screen_name:
            message = "My timeline isn't showing up in the Twitter API. Can you check on me?"
        else:
            message = ("@{}'s timeline isn't showing up in the Twitter API. "
                       "Look into that when you get a chance").format(screen_name)

    elif elapsed > hours:
        if sender == screen_name:
            message = "I'm not working. It's been more than {} hours since my last tweet. Fix me!".format(int(elapsed))
        else:
            message = 'No tweets from @{} in more than {} hours'.format(screen_name, int(elapsed))

    elif confirm:
        if sender == screen_name:
            message = "It's been {} hours since my last tweet. All is well!".format(int(elapsed))
        else:
            message = 'Just letting you know that @{} last tweeted {} hours ago'.format(screen_name, int(elapsed))

    return message


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen_name', default=None, required=False, help='screen name to check')
    parser.add_argument('--from', dest='sender', default=None, required=False,
                        help='account that will send DM notifications (defaults to screen_name)')
    parser.add_argument('--hours', type=int, default=24,
                        help="Gaps of this many hours are a problem (default: 24)")
    parser.add_argument('--to', dest='recipient', metavar='USER', type=str, default=None,
                        help='user to notify when screen_name is down. If omitted, prints to stdout')

    parser.add_argument('--confirm', action='store_true',
                        help='Always send message with the time of the most recent tweet')

    try:
        tbu
        parser.add_argument('-c', '--config', dest='config_file', metavar='PATH', default=None, type=str,
                            help='bots config file (json or yaml). By default, all accounts in the file will be checked.')
    except NameError:
        pass

    parser.add_argument('--key', type=str, help='access token')
    parser.add_argument('--secret', type=str, help='access token secret')
    parser.add_argument('--consumer-key', metavar='KEY', type=str, help='consumer key (aka consumer token)')
    parser.add_argument('--consumer-secret', metavar='SECRET', type=str, help='consumer secret')

    args = parser.parse_args()

    if getattr(args, 'config_file'):
        del args.screen_name

        conf = tbu.confighelper.parse(args.config_file)
        for bot, attrs in conf.get('users', {}).items():
            if attrs.get('whatsupbot') is False:
                continue

            user = bot if args.sender is None else args.sender
            api = tbu.API(args, screen_name=user, config_file=args.config_file)
            hours = api.config.get('whatsupbot', {}).get('hours', args.hours)
            message = whatsup(api, bot, hours, sender=user, confirm=args.confirm)

            if message:
                notify(api, message, args.recipient)

    else:
        try:
            api = tbu.API(args)
        except NameError:
            auth = tweepy.OAuthHandler(args.consumer_key, args.consumer_secret)
            auth.set_access_token(args.key, args.secret)
            api = tweepy.API(auth)

        message = whatsup(api, args.screen_name, args.hours, sender=args.sender, confirm=args.confirm)
        if message:
            notify(api, message, args.recipient)

if __name__ == '__main__':
    main()
