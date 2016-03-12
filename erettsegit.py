import argparse
import datetime

URL_TEMPLATE = "https://dari.oktatas.hu/kir/erettsegi/okev_doc/{}/{}"

FILE_NAME_TEMPLATES_V0 = ["{}_info_fl.pdf", "{}_infoforras_fl.zip",
                          "{}_info_ut.pdf", "{}_infomegoldas_ut.zip"]

FILE_NAME_TEMPLATES_V1 = ["{}_info_{}_fl.pdf", "{}_infoforras_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomegoldas_{}_ut.zip"]

FILE_NAME_TEMPLATES_V2 = ["{}_info_{}_fl.pdf", "{}_infofor_{}_fl.zip",
                          "{}_info_{}_ut.pdf", "{}_infomeg_{}_ut.zip"]

FILE_NAME_TEMPLATES_V3 = ["{}_inf_{}_fl.pdf", "{}_inffor_{}_fl.zip",
                          "{}_inf_{}_ut.pdf", "{}_infmeg_{}_ut.zip"]
def setup_cli():
  parser = argparse.ArgumentParser(description='Erettsegi Downloader')
  parser.add_argument('year', metavar='YEAR', type=yearify, help='year')
  parser.add_argument('month', metavar='MONTH', type=monthify, help='month')
  parser.add_argument('level', metavar='LEVEL', type=levelify, help='level')
  parser.add_argument('--interactive', '-i', dest='interactive',
                      action='store_true', help='defaults to non-interactive')

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

def execute_payload(year, month, level):
  file_names = gen_file_names(year, month, level)
  dl_links = build_dl_links(year, month, file_names)

if __name__ == '__main__':
  setup_cli()
