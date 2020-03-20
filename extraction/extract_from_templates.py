import argparse
import csv
import re
import sys
import tqdm
from collections import defaultdict

virus_names = ['COVID-19', 'Wuhan coronavirus', 'Wuhan seafood market pneumonia virus', 'SARS2', 'coronavirus disease 2019', 'SARS-CoV-2', '2019-nCoV']

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Extract data from text/OIE extractions')
  parser.add_argument('--template_file', required=True, type=str, default='cord19-templates.csv', help='input file')
  parser.add_argument('--text_files', required=True, type=str, nargs='+', help='Text files')
  parser.add_argument('--oie_files', type=str, nargs='+', help='OpenIE extractions')
  parser.add_argument('--tasks', type=int, nargs='+', default=None, help='Which tasks to do (if not specified, all)')

  args = parser.parse_args()

  if args.oie_files and len(args.text_files != args.oie_files):
    raise ValueError('length of text_files and oie_files arguments must be identical')

  with open(args.template_file, 'r') as f:
    csvf = csv.reader(f)
    temp_header = next(csvf)
    temp_data = list(csvf)
    if args.tasks is not None:
      temp_data = [temp_data[i] for i in args.tasks]

  temp_regexes = []
  v_regex = '('+'|'.join(virus_names)+')'
  for i, my_data in enumerate(temp_data):
    orig_regexes = my_data[3].split('\n')
    regexes = []
    for x in orig_regexes:
      if x.startswith('[Y]') or x.endswith('[Y]'):
        print(f'regex "{x}" should not start or end with [Y]', file=sys.stderr)
      elif len(x):
        regexes.append(x)
    if not len(regexes):
      temp_regexes.append(None)
      continue
    exp_regexes = []
    gname = 0
    for y in regexes:
      exp_regexes.append(y.replace('[X]', v_regex).replace('[Y]', f'(?P<G{gname}>.*?)'))
      gname += 1
    exp_regexes = '('+'|'.join(exp_regexes)+')'
    temp_regexes.append( (re.compile(exp_regexes), gname) )
  temp_recounts = [defaultdict(lambda: 0) for _ in temp_regexes]

  lines = []
  for fname in args.text_files:
    print(f'Processing {fname}', file=sys.stderr)
    with open(fname, 'r') as f:
      for line in tqdm.tqdm(f):
        for temp_rex, temp_rec in zip(temp_regexes, temp_recounts):
          if temp_rex:
            temp_rex_re, temp_rex_cnt = temp_rex
            m = re.search(temp_rex_re, line)
            if m:
              vals = [m.group(f'G{i}') for i in range(temp_rex_cnt)]
              vals = [x for x in vals if x is not None]
              assert(len(vals) == 1)
              temp_rec[vals[0]] += 1

  for temp_d, temp_rex, temp_rec in zip(temp_data, temp_regexes, temp_recounts):
    if temp_rex:
      print(f'------- {temp_d[1]} regex results')
      res = sorted(list(temp_rec.items()), key=lambda x: -x[1])
      for k, v in res:
        print(f'{v}\t{k} {temp_d[4]}')
      print()

