import argparse
import datetime
import sys
import os
import urllib.request
import zipfile

URL_TEMPLATE = "https://dari.oktatas.hu/kir/erettsegi/okev_doc/{}/{}"

FILE_NAME_TEMPLATES_V0 = ["{}_info_fl.pdf", "{}_infoforras_fl.zip",
                          "{}_info_ut.pdf", "{}_infomegoldas_ut.zip"]

FILE_NAME_TEMPLATES_V1 = ["{}_info_{}_fl.pdf", "{}_infoforras_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomegoldas_{}_ut.zip"]

FILE_NAME_TEMPLATES_V2 = ["{}_info_{}_fl.pdf", "{}_infofor_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomeg_{}_ut.zip"]

FILE_NAME_TEMPLATES_V3 = ["{}_inf_{}_fl.pdf", "{}_inffor_{}_fl.zip",
                          "{}_inf_{}_ut.pdf", "{}_infmeg_{}_ut.zip"]


def should_go_interactive():
    if len(sys.argv) >= 2 and sys.argv[1] in ['--interactive', '-i']:
        return True  # interactive cli switch was provided
    if sys.argv[0] == '':
        return True  # we are inside a REPL
    if os.name == 'nt' and 'PROMPT' not in os.environ:
        return True  # was double-clicked on Windows (would close instantly)

    return False


def start_ia_ui():  # start the interactive UI
    exit_code = 0
    print('Erettsegi Downloader')

    try:
        year = yearify(input('year: '))
        month = monthify(input('month: '))
        level = levelify(input('level: '))
        execute_payload(year, month, level, interactive=True)
    except (argparse.ArgumentTypeError, OSError) as ex:
        print(ex)
        exit_code = 1
    else:
        print('done')
    finally:
        input('press enter to quit...')
        exit(exit_code)


def setup_cli():
    parser = argparse.ArgumentParser(description='Erettsegi Downloader')
    parser.add_argument('year', metavar='YEAR', type=yearify, help='year')
    parser.add_argument('month', metavar='MONTH', type=monthify, help='month')
    parser.add_argument('level', metavar='LEVEL', type=levelify, help='level')
    parser.add_argument('--interactive',
                        '-i',
                        dest='interactive',
                        action='store_true',
                        help='defaults to non-interactive')

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
        raise argparse.ArgumentTypeError('incorrect year')

    if 0 <= year <= 999:
        year = 2000 + year  # e.g. fix 16 to 2016
    if not 2005 <= year <= datetime.date.today().year:
        raise argparse.ArgumentTypeError('incorrect year')

    return year


def monthify(input_month: str):
    try:
        month = int(input_month)  # see if it's a valid number
        if month in [2, 5, 10]:
            return month
    except ValueError:  # try parsing as textual month
        first_letter = input_month[0].lower()
        if first_letter in ['m', 't']:
            return 5  # for May, majus, tavasz, etc.
        elif first_letter in ['o', 'ő']:
            return 10  # for Oct, okt, ősz, etc.
        elif first_letter == 'f':
            return 2

    raise argparse.ArgumentTypeError('incorrect month')  # couldn't parse


def levelify(input_level: str):
    if input_level[0] == 'm': input_level = 'k'  # mid -> (k)ozep
    if input_level[0] == 'a': input_level = 'e'  # advanced -> (e)melt

    if input_level[0] not in ['k', 'e']:
        raise argparse.ArgumentTypeError('incorrect level')
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


def create_and_enter_dl_dir(year: int, month: int, level: str):
    dir_name = "{}-{}-{}".format(year, month, level)
    try:
        os.mkdir(dir_name)
        os.chdir(dir_name)
    except OSError:
        print('already downloaded')
        exit(1)


def dl_progressbar(block_num, block_size, total_size):
    received = block_num * block_size
    if total_size > 0:
        percentage = int(received * 100) / total_size
        if percentage > 100:
            # avoid displaying more than 100% from rounding errors..
            percentage = 100
        progress = round(percentage / (100 / 65))

        out = "\r{:10.1f}%   {}".format(percentage,  # "the progressbar"
                                        progress * "\u2588" +
                                        (65 - progress) * ' ' + '|')
        sys.stdout.write(out)
        sys.stdout.flush()

        if received >= total_size:
            sys.stdout.write("\n")  # file done
    else:
        print("error, read: {}\n".format(received, ))


def save_file(url: str, name: str, interactive=False):
    dl_file = urllib.request.URLopener()
    try:
        if interactive:  # only display progress if in interactive mode
            dl_file.retrieve(url, name, dl_progressbar)
        else:  # download sliently, exit code indicates result
            dl_file.retrieve(url, name)
    except:
        raise ConnectionError("a network error occured")

    if name.endswith('.zip'):  # extract it if it's a zip
        archive = zipfile.ZipFile(name)
        archive.extractall()
        archive.close()
        os.remove(name)


def execute_payload(year: int, month: int, level: str, interactive=False):
    # generates links, downloads from them, and extracts archives
    file_names = gen_file_names(year, month, level)
    dl_links = build_dl_links(year, month, file_names)

    create_and_enter_dl_dir(year, month, level)
    for dl_link, file_name in zip(dl_links, file_names):
        save_file(dl_link, file_name, interactive)
    os.chdir('..')  # exit the dl dir


if __name__ == '__main__':
    setup_cli()
