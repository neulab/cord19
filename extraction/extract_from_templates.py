import argparse
import csv
import re
import sys
import tqdm
from collections import defaultdict

virus_names = ['COVID-19', 'Wuhan coronavirus', 'Wuhan seafood market pneumonia virus', 'SARS2', 'coronavirus disease 2019', 'SARS-CoV-2', '2019-nCoV']

oie_span_re = r'#[0-9]+,[0-9]+'

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Extract data from text/OIE extractions')
  parser.add_argument('--template_file', required=True, type=str, default='cord19-templates.csv', help='input file')
  parser.add_argument('--text_files', type=str, nargs='+', help='Text files')
  parser.add_argument('--oie_files', type=str, nargs='+', help='OpenIE extractions')
  parser.add_argument('--tasks', type=int, nargs='+', default=None, help='Which tasks to do (if not specified, all)')

  args = parser.parse_args()

  with open(args.template_file, 'r') as f:
    csvf = csv.reader(f)
    temp_header = next(csvf)
    temp_data = list(csvf)
    if args.tasks is not None:
      temp_data = [temp_data[i] for i in args.tasks]

  # Create regexes
  temp_regexes, oie_regexes = [], []
  v_regex = '('+'|'.join(virus_names)+')'
  for i, my_data in enumerate(temp_data):
    # Text extraction
    orig_regexes = my_data[4].split('\n')
    regexes = []
    for x in orig_regexes:
      if x.startswith('[Y]') or x.endswith('[Y]'):
        print(f'regex "{x}" should not start or end with [Y]', file=sys.stderr)
      elif len(x):
        regexes.append(x)
    if not len(regexes):
      temp_regexes.append(None)
    else:
      regexes = [x.replace('[X]', v_regex).replace('[Y]', f'(?P<G{i}>.*?)') for (i,x) in enumerate(regexes)]
      regexes = '('+'|'.join(regexes)+')'
      temp_regexes.append( (re.compile(regexes), len(regexes), my_data[6]) )
    # OIE regexes
    regexes = my_data[3].split('\n')
    if not len(regexes) or not len(regexes[0]):
      oie_regexes.append(None)
    else:
      regexes = [x.replace('[X]', v_regex).replace('[B]', '\\|\\|\\|') for (i,x) in enumerate(regexes)]
      regexes = '('+'|'.join(regexes)+')'
      oie_regexes.append( re.compile(regexes) )
  temp_recounts = [defaultdict(lambda: []) for _ in temp_regexes]
  oie_recounts = [defaultdict(lambda: []) for _ in oie_regexes]

  # Process text
  lines = []
  for file_id, fname in enumerate(args.text_files if args.text_files else []):
    print(f'Processing {fname}', file=sys.stderr)
    with open(fname, 'r') as f:
      for line_id, line in tqdm.tqdm(enumerate(f)):
        for temp_id, (temp_rex, temp_rec) in enumerate(zip(temp_regexes, temp_recounts)):
          if temp_rex:
            temp_rex_re, temp_rex_cnt, temp_rex_type = temp_rex
            m = re.search(temp_rex_re, line)
            if m:
              if temp_rex_type == 'ydata':
                vals = [m.group(f'G{i}') for i in range(temp_rex_cnt)]
                vals = [x for x in vals if x is not None]
                assert(len(vals) == 1)
                key = vals[0]
              else:
                key = m.group(1)
              temp_rec[key].append( (file_id,line_id) )

  # Process oie
  lines = []
  for file_id, fname in enumerate(args.oie_files if args.oie_files else []):
    print(f'Processing {fname}', file=sys.stderr)
    with open(fname, 'r') as f:
      for line_id, line in tqdm.tqdm(enumerate(f)):
        line = re.sub(oie_span_re,'',line)
        for extraction in line.split('\t'):
          for temp_id, (oie_rex, oie_rec) in enumerate(zip(oie_regexes, oie_recounts)):
            if oie_rex:
              m = re.search(oie_rex, extraction)
              if m:
                key = extraction.strip().replace('|||', ' ')
                oie_rec[key].append( (file_id,line_id) )

  for temp_d, temp_rex, temp_rec, oie_rex, oie_rec in zip(temp_data, temp_regexes, temp_recounts, oie_regexes, oie_recounts):
    if temp_rex:
      print(f'------- {temp_d[1]} regex results')
      res = sorted(list(temp_rec.items()), key=lambda x: -len(x[1]))
      for k, v in res:
        l = len(v)
        files = ' '.join([f'{args.text_files[fid]}:{lid}' for (fid,lid) in v])
        print(f'{l}\t{k} {temp_d[5]}\t{files}')
      print()
    if oie_rex:
      print(f'------- {temp_d[1]} regex results')
      res = sorted(list(oie_rec.items()), key=lambda x: -len(x[1]))
      for k, v in res:
        l = len(v)
        files = ' '.join([f'{args.oie_files[fid]}:{lid}' for (fid,lid) in v])
        print(f'{l}\t{k} {temp_d[5]}\t{files}')
      print()

