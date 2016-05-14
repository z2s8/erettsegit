import argparse
import datetime
import locale
import re
import sys
import os
import urllib.request
import zipfile
from enum import Enum

VERSION = '0.0.1'

URL_TEMPLATE = "https://dari.oktatas.hu/kir/erettsegi/okev_doc/{}/{}"

FILE_NAME_TEMPLATES_V0 = ["{}_info_fl.pdf", "{}_infoforras_fl.zip",
                          "{}_info_ut.pdf", "{}_infomegoldas_ut.zip"]

FILE_NAME_TEMPLATES_V1 = ["{}_info_{}_fl.pdf", "{}_infoforras_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomegoldas_{}_ut.zip"]

FILE_NAME_TEMPLATES_V2 = ["{}_info_{}_fl.pdf", "{}_infofor_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomeg_{}_ut.zip"]

FILE_NAME_TEMPLATES_V3 = ["{}_inf_{}_fl.pdf", "{}_inffor_{}_fl.zip",
                          "{}_inf_{}_ut.pdf", "{}_infmeg_{}_ut.zip"]

# e_* = error, i_* = info, h_* = help, c_* = common
MessageType = Enum('MessageType',
                   ['c_year', 'c_month', 'c_level', 'e_file', 'e_network',
                    'e_input', 'h_desc', 'h_ia', 'i_ok', 'i_quit'])

MESSAGES = {'HU': {}, 'EN': {}}

MESSAGES['EN'] = {
    MessageType.c_year: 'year',
    MessageType.c_month: 'month',
    MessageType.c_level: 'level',
    MessageType.e_input: "incorrect {}",
    MessageType.e_file: 'already downloaded',
    MessageType.e_network: 'a network error occured',
    MessageType.i_ok: 'done',
    MessageType.i_quit: 'press enter to quit...',
    MessageType.h_ia: 'defaults to non-interactive',
    MessageType.h_desc: "ErettSeGit - Informatics 'Erettsegi' Downloader - {}"
                        .format(VERSION)
}

MESSAGES['HU'] = {
    MessageType.c_year: 'év',
    MessageType.c_month: 'hónap',
    MessageType.c_level: 'szint',
    MessageType.e_input: "hibás {}",
    MessageType.e_file: 'már letöltve',
    MessageType.e_network: 'hálózati hiba történt',
    MessageType.h_ia: 'alapértelmezetten nem interaktív',
    MessageType.i_ok: 'kész',
    MessageType.i_quit: 'enter a kilépéshez...',
    MessageType.h_ia: 'alapértelmezetten nem interaktív',
    MessageType.h_desc: "ErettSeGit - Informatika Érettségi Letöltő - {}"
                        .format(VERSION)
}


# FancyURLopener with precise User-Agent header
class AppURLopener(urllib.request.FancyURLopener):
    version = 'erettsegit/{} - github.com/z2s8/erettsegit'.format(VERSION)


def get_lang():
    if os.getenv('ERETTSEGIT_LANG') is not None:
        return os.getenv('ERETTSEGIT_LANG')

    sys_lang_codes = str(locale.getdefaultlocale()[0])
    hun_regex = r'\bHU(N)?\b'
    for lang_code in re.split(r'[-_/. ]', sys_lang_codes):
        if re.search(hun_regex, lang_code, flags=re.IGNORECASE) is not None:
            os.environ['ERETTSEGIT_LANG'] = 'HU'
            return 'HU'

    # for every language detected not Hungarian we'll go with English
    os.environ['ERETTSEGIT_LANG'] = 'EN'
    return 'EN'


def message_for(event: MessageType, extra: MessageType = None):
    lang = get_lang()
    return MESSAGES[lang][event].format(MESSAGES[lang].get(extra))


def should_go_interactive():
    if len(sys.argv) >= 2 and sys.argv[1] in ['--interactive', '-i']:
        # interactive cli switch was provided
        return True
    if sys.argv[0] == '':
        # we are inside a REPL, e.g. IDLE shell
        return True
    if os.name == 'nt' and 'PROMPT' not in os.environ:
        # launched with doubleclick on Windows (would close instantly)
        return True

    return False


def start_ia_ui():  # start the interactive UI
    exit_code = 0
    print(message_for(MessageType.h_desc))
    try:
        year = yearify(input("{}: ".format(message_for(MessageType.c_year))))

        month = monthify(input("{}: "
                               .format(message_for(MessageType.c_month))))
        level = levelify(input("{}: "
                               .format(message_for(MessageType.c_level))))
        execute_payload(year, month, level, interactive=True)
    except (argparse.ArgumentTypeError, OSError) as ex:
        if type(ex) == argparse.ArgumentTypeError:
            print(ex)
        exit_code = 1
    else:
        print(message_for(MessageType.i_ok))
    finally:
        input(message_for(MessageType.i_quit))
        exit(exit_code)


def setup_cli():
    parser = argparse.ArgumentParser(description=
                                     message_for(MessageType.h_desc))

    parser.add_argument('year',
                        metavar=message_for(MessageType.c_year).upper(),
                        type=yearify, help=message_for(MessageType.c_year))
    parser.add_argument('month',
                        metavar=message_for(MessageType.c_month).upper(),
                        type=monthify, help=message_for(MessageType.c_month))
    parser.add_argument('level',
                        metavar=message_for(MessageType.c_level).upper(),
                        type=levelify, help=message_for(MessageType.c_level))
    parser.add_argument('--interactive', '-i', dest='interactive',
                        action='store_true',
                        help=message_for(MessageType.h_ia))

    if should_go_interactive():
        start_ia_ui()
    else:  # stay in CLI mode
        args = parser.parse_args()
        execute_payload(args.year, args.month, args.level)


def yearify(input_year: str):
    year = None
    try:
        year = int(input_year)
    except:
        raise argparse.ArgumentTypeError(
                message_for(MessageType.e_input, MessageType.c_year))

    if 0 <= year <= 99:
        year = 2000 + year  # e.g. fix 16 to 2016
    if not 2005 <= year <= datetime.date.today().year:
        raise argparse.ArgumentTypeError(
                message_for(MessageType.e_input, MessageType.c_year))

    return year


def monthify(input_month: str):
    try:
        month = int(input_month)  # see if it's a valid number
        if month in [2, 5, 10]:
            return month
    except ValueError:  # try parsing as textual month
        first_letter = input_month[0].lower()
        if first_letter in ['m', 't']:
            return 5   # for May, majus, tavasz, etc.
        elif first_letter in ['o', 'ő']:
            return 10  # for Oct, okt, ősz, etc.
        elif first_letter == 'f':
            return 2   # for Feb, februar, etc.

    # couldn't parse
    raise argparse.ArgumentTypeError(
            message_for(MessageType.e_input, MessageType.c_month))


def levelify(input_level: str):
    if input_level[0] == 'm': input_level = 'k'  # mid -> (k)ozep [HUN]
    if input_level[0] == 'a': input_level = 'e'  # advanced -> (e)melt [HUN]

    if input_level[0] not in ['k', 'e']:
        raise argparse.ArgumentTypeError(
            message_for(MessageType.e_input, MessageType.c_level))
    return input_level[0]

# gen_file_names and build_dl_links tries to handle
# the inconsistent naming of downloads on the officeal site


def gen_file_names(year: int, month: int, level: str):
    year_part = str(year)[2:4]  # e.g. 2016 -> 16
    month_part = 'febr'  # for month = 2
    if month == 5:
        month_part = 'maj'
    elif month == 10:
        month_part = 'okt'
    date_part = year_part + month_part

    current_templates = FILE_NAME_TEMPLATES_V3  # default: use newest naming
    if year == 2005 and month == 5:
        current_templates = FILE_NAME_TEMPLATES_V0
    elif year < 2009:
        current_templates = FILE_NAME_TEMPLATES_V1
    elif 100 * year + month < 100 * 2011 + 10:
        current_templates = FILE_NAME_TEMPLATES_V2

    current_files = []  # list of file names to download
    for file_name in current_templates:
        current_files.append(file_name.format(level, date_part))

    return current_files


def build_dl_links(year: int, month: int, documents):
    # List[str] is only supported since 3.5, so leaving out for now (documents)
    date_part = "erettsegi_{}".format(year)
    if month == 10 and year > 2006:
        date_part += '/oktober'
    elif month == 10 and year == 2005:
        date_part = '2005_osz'
    elif month == 2 and year == 2006:
        date_part = '2006_1'

    current_links = []  # links to download
    for document in documents:
        current_links.append(URL_TEMPLATE.format(date_part, document))

    return current_links


def create_and_enter_dl_dir(year: int, month: int, level: str,
                            interactive=False):

    dir_name = "{}-{}-{}".format(year, month, level)
    try:
        os.mkdir(dir_name)
        os.chdir(dir_name)
    except OSError as ex:
        print(message_for(MessageType.e_file))  # dir already exists
        if interactive:
            # when interactive wait for user before exiting
            raise ex
        else:
            exit(1)


def dl_progressbar(block_num, block_size, total_size):
    received = block_num * block_size
    percentage = int(received * 100) / total_size
    if percentage > 100:
        # avoid displaying more than 100% from rounding errors..
        percentage = 100
    progress = round(percentage / (100 / 65))

    # "DIY progressbar"
    out = "\r{:10.1f}%   {}" \
          .format(percentage, progress * u'█' + (65 - progress) * ' ' + '|')

    sys.stdout.write(out)
    sys.stdout.flush()

    if received >= total_size:  # file done
        sys.stdout.write("\n")
        sys.stdout.flush()


def save_file(url: str, name: str, interactive=False):
    dl_file = AppURLopener()
    try:
        if interactive:
            # only display progress if in interactive mode
            dl_file.retrieve(url, name, dl_progressbar)
        else:
            # download sliently, exit code indicates result
            dl_file.retrieve(url, name)
    except:
        raise ConnectionError(message_for(MessageType.e_network))

    if name.endswith('.zip'):  # extract it if it's a zip
        archive = zipfile.ZipFile(name)
        archive.extractall()
        archive.close()
        os.remove(name)


def execute_payload(year: int, month: int, level: str, interactive=False):
    # generates links, downloads from them, and extracts archives
    file_names = gen_file_names(year, month, level)
    dl_links = build_dl_links(year, month, file_names)

    create_and_enter_dl_dir(year, month, level, interactive)
    for dl_link, file_name in zip(dl_links, file_names):
        save_file(dl_link, file_name, interactive)
    os.chdir('..')  # exit current download's directory


if __name__ == '__main__':
    setup_cli()
