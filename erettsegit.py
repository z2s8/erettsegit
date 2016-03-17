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
  if len(sys.argv) == 2 and sys.argv[1] in ['--interactive', '-i']:
    return True
  if sys.argv[0] == '':
    return True
  if os.name == 'nt' and 'PROMPT' not in os.environ:
    return True
  return False

def start_ia_ui():
  exit_code = 0
  print('Erettsegi Downloader')

  try:
    year = yearify(input('year: '))
    month = monthify(input('month: '))
    level = levelify(input('level: '))
    execute_payload(year, month, level, interactive=True)
  except (argparse.ArgumentTypeError, OSError, Exception) as ex:
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
  parser.add_argument('--interactive', '-i', dest='interactive',
                      action='store_true', help='defaults to non-interactive')

  if should_go_interactive():
    start_ia_ui()
  else:
    args = parser.parse_args()
    execute_payload(args.year, args.month, args.level)

def yearify(input_year):
  year = None
  try:
    year = int(input_year)
  except:
    raise argparse.ArgumentTypeError('incorrect year')

  if 0 <= year <= 999:
    year = 2000 + year
  if not 2005 <= year <= datetime.date.today().year:
    raise argparse.ArgumentTypeError('incorrect year')

  return year

def monthify(input_month):
  try:
    month = int(input_month)
    if month in [2, 5, 10]:
      return month
    raise argparse.ArgumentTypeError('incorrect month')
  except:
    if input_month[0] in ['m', 't']:
      return 5
    elif input_month[0] in ['o', 'ő']:
      return 10
    elif input_month[0] == 'f':
      return 2
    raise argparse.ArgumentTypeError('incorrect month')

def levelify(input_level):
  if input_level[0] == 'm': input_level = 'k'
  if input_level[0] == 'a': input_level = 'e'

  if input_level[0] not in ['k', 'e']:
    raise argparse.ArgumentTypeError('incorrect level')
  return input_level[0]

def gen_file_names(year: int, month: int, level: str):
  year_part = str(year)[2:4]
  month_part = 'febr'
  if month == 5:
    month_part = 'maj'
  elif month == 10:
    month_part = 'okt'
  date_part = year_part + month_part

  current_templates = FILE_NAME_TEMPLATES_V3
  if year == 2005 and month == 5:
    current_templates = FILE_NAME_TEMPLATES_V0
  elif year < 2009:
    current_templates = FILE_NAME_TEMPLATES_V1
  elif 100 * year + month < 100 * 2011 + 10:
    current_templates = FILE_NAME_TEMPLATES_V2

  current_files = []
  for file_name in current_templates:
    current_files.append(file_name.format(level, date_part))

  return current_files

def build_dl_links(year: int, month: int, documents):
  date_part = "erettsegi_{}".format(year)
  if month == 10 and year > 2006:
    date_part += '/oktober'
  elif month == 10 and year == 2005:
    date_part = '2005_osz'
  elif month == 2 and year == 2006:
    date_part = '2006_1'

  current_links = []
  for document in documents:
    current_links.append(URL_TEMPLATE.format(date_part, document))

  return current_links

def create_and_enter_dl_dir(year, month, level):
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
      percentage = 100
    progress = round(percentage / (100 / 70))

    out = "\r{:10.1f}%\t".format(percentage) + progress * "\u2588" \
        + (70 - progress) * ' ' + '|'
    sys.stdout.write(out)
    sys.stdout.flush()
    if received >= total_size:
      sys.stdout.write("\n")
  else:
    sys.stdout.write("read {}\n".format(received,))

def save_file(url, name, interactive=False): 
  dl_file = urllib.request.URLopener()
  try:
    if interactive:
      dl_file.retrieve(url, name, dl_progressbar)
    else:
      dl_file.retrieve(url, name)
  except:
    raise Exception("network error")

  if name.endswith('.zip'):
    zf = zipfile.ZipFile(name)
    zf.extractall()
    zf.close()
    os.remove(name)

def execute_payload(year, month, level, interactive=False):
  file_names = gen_file_names(year, month, level)
  dl_links = build_dl_links(year, month, file_names)

  create_and_enter_dl_dir(year, month, level)
  for dl_link, file_name in zip(dl_links, file_names):
    save_file(dl_link, file_name, interactive)
  os.chdir('..')

if __name__ == '__main__':
  setup_cli()
