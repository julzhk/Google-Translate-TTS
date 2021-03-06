#!/usr/bin/python

import sys
import argparse
import re
import urllib, urllib2
import time
from collections import namedtuple

API_MAX_SENTENCE_LENGTH = 100 # The text-to-speech API only accepts this many words at a time.
API_URL = "http://translate.google.com/translate_tts?tl=%s&q=%s&total=%s&idx=%s"
DEFAULT_OUTPUT_FILENAME = 'output.mp3'
REQUEST_HEADERS = {"Host": "translate.google.com",
                   "Referer": "http://www.gstatic.com/translate/sound_player2.swf",
                   "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) "
                   "AppleWebKit/535.19 (KHTML, like Gecko) "
                   "Chrome/18.0.1025.163 Safari/535.19"
                  }
WAIT_BETWEEN_REQUESTS = .5  # seconds

audio_args = namedtuple('audio_args', ['language', 'output'])

def split_text(input_text, max_length=API_MAX_SENTENCE_LENGTH):
    """
    Try to split between sentences to avoid interruptions mid-sentence.
    Failing that, split between words.
    See split_text_rec
    :param input_text: String to convert to Mp3
    :param max_length: Integer: Maximum unbroken string length accepted by the API
    """

    def split_text_rec(input_text, regexps, max_length=max_length):
        """
        Split a string into substrings which are at most max_length.
        Tries to make each substring as long as possible without exceeding
        max_length.
        Will use the first regexp in regexps to split the input into
        substrings.
        If it it impossible to make all the segments less or equal than
        max_length with a regexp then the next regexp in regexps will be used
        to split those into subsegments.
        If there are still substrings who are too big after all regexps have
        been used then the substrings, those will be split at max_length.

        Args:
            input_text: The text to split.
            regexps: A list of regexps.
                If you want the separator to be included in the substrings you
                can add parenthesis around the regular expression to create a
                group. Eg.: '[ab]' -> '([ab])'

        Returns:
            a list of strings of maximum max_length length.
        """
        if (len(input_text) <= max_length):
            return [input_text]
        #mistakenly passed a string instead of a list
        if isinstance(regexps, basestring):
            regexps = [regexps]
        regexp = regexps.pop(0) if regexps else '(.{%d})' % max_length
        text_list = re.split(regexp, input_text)
        combined_text = []
        #first segment could be >max_length
        combined_text.extend(split_text_rec(text_list.pop(0), regexps, max_length))
        for val in text_list:
            current = combined_text.pop()
            concat = current + val
            if (len(concat) <= max_length):
                combined_text.append(concat)
            else:
                combined_text.append(current)
                #val could be >max_length
                combined_text.extend(split_text_rec(val, regexps, max_length))
        return combined_text
    return split_text_rec(input_text.replace('\n', ''),
                          ['([\,|\.|;]+)', '( )'])


def audio_extract(input_text='', args=None):
    # This accepts :
    #   a dict,
    #   an audio_args named tuple
    #   or arg parse object
    if args is None:
        args = audio_args(language='en', output=DEFAULT_OUTPUT_FILENAME)
    if type(args) is dict:
        args = audio_args(
            language=args.get('language', 'en'),
            output=args.get('output', DEFAULT_OUTPUT_FILENAME)
        )
    #process input_text into chunks
    #Google TTS only accepts up to (and including) 100 characters long texts.
    #Split the text in segments of maximum 100 characters long.
    combined_text = split_text(input_text)
    #download chunks and write them to the output file
    with open(args.output, 'w') as write_file:
        for idx, val in enumerate(combined_text):
            mp3url = API_URL % (
                args.language,
                urllib.quote(val),
                len(combined_text),
                idx)
            req = urllib2.Request(mp3url, '', REQUEST_HEADERS)
            sys.stdout.write('.')
            sys.stdout.flush()
            if len(val) > 0:
                try:
                    response = urllib2.urlopen(req)
                    write_file.write(response.read())
                    time.sleep(WAIT_BETWEEN_REQUESTS)
                except urllib2.URLError as e:
                    print ('%s' % e)
    print('MP3 saved to %s' % args.output)


def text_to_speech_mp3_argparse():
    description = 'Google TTS Downloader.'
    parser = argparse.ArgumentParser(description=description,
                                     epilog='tunnel snakes rule')
    parser.add_argument('-o', '--output',
                        action='store', nargs='?',
                        help='Filename to output audio to',
                        default=DEFAULT_OUTPUT_FILENAME)
    parser.add_argument('-l', '--language',
                        action='store',
                        nargs='?',
                        help='Language to output text in.', default='en')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file',
                       type=argparse.FileType('r'),
                       help='File to read from.')
    group.add_argument('-s', '--string',
                       action='store',
                       nargs='+',
                       help='A text string to convert to a speech file.')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args()


if __name__ == "__main__":
    args = text_to_speech_mp3_argparse()
    if args.file:
        input_text = args.file.read()
    if args.string:
        input_text = ' '.join(map(str, args.string))
    audio_extract(input_text=input_text, args=args)
