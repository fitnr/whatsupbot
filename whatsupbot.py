#!/usr/bin/env python
from __future__ import print_function
import argparse
from datetime import datetime
try:
    import twitter_bot_utils as tbu
except ImportError:
    import tweepy


def last_tweet(api, screen_name):
    '''Hours since last tweet. Returns float.'''
    try:
        created_at = api.user_timeline(screen_name, count=1)[0].created_at
        now = datetime.now()

        return (now - created_at).total_seconds() / 3600.
    except (TypeError, IndexError):
        return False


def notify(api, screen_name, elapsed=False):
    if elapsed:
        text = "I'm not working. It's been {} hours since my last tweet. Fix me!".format(int(elapsed))
    else:
        text = "I'm not working. Fix me!"

    api.send_direct_message(screen_name=screen_name, text=text)


def whatsup(api, screen_name, hours, recipient=None):
    elapsed = last_tweet(api, screen_name)

    if elapsed > hours:
        if recipient:
            notify(api, recipient, elapsed)
        else:
            print('no tweets from', screen_name, 'in the last', int(elapsed), 'hours')


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--screen_name', default=None, required=False, help='screen name to check')
    parser.add_argument('--hours', type=int, default=24,
                        help="Gaps of this many hours are a problem (default: 24)")
    parser.add_argument('--notify', dest='recipient', metavar='USER', type=str, default=None,
                        help='user to notify when screen_name is down')

    try:
        tbu
        parser.add_argument('-c', '--config', dest='config_file', metavar='PATH', default=None, type=str,
                            help='bots config file (json or yaml). All bots in the file will be checked.')
    except NameError:
        pass

    parser.add_argument('--key', type=str, help='access token')
    parser.add_argument('--secret', type=str, help='access token secret')
    parser.add_argument('--consumer-key', metavar='KEY', type=str, help='consumer key (aka consumer token)')
    parser.add_argument('--consumer-secret', metavar='SECRET', type=str, help='consumer secret')

    args = parser.parse_args()

    if getattr(args, 'config_file'):
        bots = tbu.confighelper.parse(args.config_file).get('users').keys()

        for bot in bots:
            api = tbu.API(screen_name=bot, config_file=args.config_file)

            if api.config.get('whatsupbot') is False:
                continue

            hours = api.config.get('whatsupbot', {}).get('hours', args.hours)
            whatsup(api, bot, hours, args.recipient)

    else:
        try:
            api = tbu.API(args)
        except NameError:
            auth = tweepy.OAuthHandler(args.consumer_key, args.consumer_secret) 
            auth.set_access_token(args.key, args.secret)
            api = tweepy.API(auth)

        whatsup(api, args.screen_name, args.hours, args.recipient)

if __name__ == '__main__':
    main()
