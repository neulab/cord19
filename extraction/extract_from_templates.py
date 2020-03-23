import argparse
import csv
import os
import re
import shutil
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
  parser.add_argument('--html_dir', type=str, required=True, help='The directory where we output files')
  parser.add_argument('--tasks', type=int, nargs='+', default=None, help='Which tasks to do (if not specified, all)')

  args = parser.parse_args()
  if args.oie_files and len(args.oie_files) != len(args.text_files):
    raise ValueError('Lengths of the args.oie_files and args.text_files arguments must be the same')

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
      regex_cnt = len(regexes)
      regexes = '('+'|'.join(regexes)+')'
      temp_regexes.append( (re.compile(regexes), regex_cnt, my_data[6]) )
    # OIE regexes
    regexes = my_data[3].split('\n')
    if not len(regexes) or not len(regexes[0]):
      oie_regexes.append(None)
    else:
      regexes = [x.replace('[X]', v_regex).replace('[B]', '\\|\\|\\|') for (i,x) in enumerate(regexes)]
      regexes = '('+'|'.join(regexes)+')'
      oie_regexes.append( re.compile(regexes) )

  # This is using a dictionary to store the results to de-duplicate lines
  temp_recounts = [defaultdict(lambda: {}) for _ in temp_regexes]
  oie_recounts = [defaultdict(lambda: {}) for _ in oie_regexes]

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
              if temp_rex_type == 'yonly':
                vals = [m.group(f'G{i}') for i in range(temp_rex_cnt)]
                vals = [x for x in vals if x is not None]
                assert(len(vals) == 1)
                key = vals[0]
              else:
                key = m.group(1)
              temp_rec[key][line] = (file_id,line_id)

  # Process oie
  lines = []
  for file_id, fname in enumerate(args.oie_files if args.oie_files else []):
    print(f'Processing {fname}', file=sys.stderr)
    with open(fname, 'r') as f, open(args.text_files[file_id], 'r') as ft:
      for line_id, (line, linet) in tqdm.tqdm(enumerate(zip(f, ft))):
        line = re.sub(oie_span_re,'',line)
        extractions = line.split('\t')
        for temp_id, (oie_rex, oie_rec) in enumerate(zip(oie_regexes, oie_recounts)):
          if oie_rex:
            # Use a heuristic of only keeping the shortest extraction that matches
            best_extraction = None
            for extraction in extractions:
              m = re.search(oie_rex, extraction)
              if m:
                key = extraction.strip().replace('|||', ' ')
                if not best_extraction or len(best_extraction[0]) > len(key):
                  best_extraction = (key, linet, file_id, line_id)
            if best_extraction:
              (key, linet, file_id, line_id) = best_extraction
              oie_rec[key][linet] = (file_id,line_id)

  if not os.path.exists(args.html_dir):
      os.makedirs(args.html_dir)
  shutil.copy2('main.css', f'{args.html_dir}/main.css')

  def page_head(title):
    return f'<html><head><link rel="stylesheet" type="text/css" href="main.css"><title>{title}</title></head><body><h1>{title}</h1>'

  with open(f'{args.html_dir}/index.html', 'w') as findex:
    print(page_head('CORD-19 Information Extraction Report')+'<ul>', file=findex)
    for i, (temp_d, temp_rex, temp_rec, oie_rex, oie_rec) in enumerate(zip(temp_data, temp_regexes, temp_recounts, oie_regexes, oie_recounts)):
      if temp_rex or oie_rex:
        fname = f'report-{i}.html'
        l = (len(temp_rec) if temp_rec else 0) + (len(oie_rec) if oie_rec else 0)
        print(f'<li><a href="{fname}">{temp_d[2]}</a> ({l} results)</li>', file=findex)
        with open(f'{args.html_dir}/{fname}', 'w') as f:
          print(page_head(temp_d[2]), file=f)
          print('<p><a href="index.html">&lt;&lt; Back to Top</a></p>', file=f)
          # TODO: Copied code here is not ideal, can we fix?
          if temp_rex:
            print('<h2>Textual Template Results</h2><table>', file=f)
            res = sorted(list(temp_rec.items()), key=lambda x: -len(x[1]))
            for k, v in res:
              l = len(v)
              print(f'<tr><th>{k} {temp_d[5]} (count: {l})</th></tr>', file=f)
              for text, (fid, lid) in v.items():
                print(f'<tr><td colspan=2>{text}</td></tr>', file=f)
            print('</table>', file=f)
          if oie_rex:
            print('<h2>Information Extraction Results</h2><table>', file=f)
            res = sorted(list(oie_rec.items()), key=lambda x: -len(x[1]))
            for k, v in res:
              l = len(v)
              print(f'<tr><th>{k} {temp_d[5]} (count: {l})</th></tr>', file=f)
              for text, (fid, lid) in v.items():
                print(f'<tr><td colspan=2>{text}</td></tr>', file=f)
            print('</table>', file=f)
          print('</ul></body></html>', file=f)
    print('</ul></body></html>', file=findex)
