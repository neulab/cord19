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
  parser.add_argument('--text_files', type=str, nargs='+', required=True, help='Text files')
  parser.add_argument('--oie_files', type=str, nargs='+', required=True, help='OpenIE extractions')
  parser.add_argument('--html_dir', type=str, required=True, help='The directory where we output files')
  parser.add_argument('--tasks', type=int, nargs='+', default=None, help='Which tasks to do (if not specified, all)')
  parser.add_argument('--raw_data_dir', type=str, help='A link to the raw data JSON files')

  args = parser.parse_args()
  if args.oie_files and len(args.oie_files) != len(args.text_files):
    raise ValueError('Lengths of the args.oie_files and args.text_files arguments must be the same')

  with open(args.template_file, 'r') as f:
    csvf = csv.reader(f)
    text_header = next(csvf)
    temp_data = list(csvf)
    if args.tasks is not None:
      temp_data = [temp_data[i] for i in args.tasks]

  # Create regexes
  text_regexes, oie_regexes = [], []
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
      text_regexes.append(None)
    else:
      regexes = [x.replace('[X]', v_regex).replace('[Y]', f'(?P<G{i}>.*?)') for (i,x) in enumerate(regexes)]
      regex_cnt = len(regexes)
      regexes = '('+'|'.join(regexes)+')'
      text_regexes.append( (re.compile(regexes), regex_cnt, my_data[6]) )
    # OIE regexes
    regexes = my_data[3].split('\n')
    if not len(regexes) or not len(regexes[0]):
      oie_regexes.append(None)
    else:
      regexes = [x.replace('[X]', v_regex).replace('[B]', '\\|\\|\\|') for (i,x) in enumerate(regexes)]
      regexes = '('+'|'.join(regexes)+')'
      oie_regexes.append( re.compile(regexes) )

  # This is using a dictionary to store the results to de-duplicate lines
  text_recounts = [defaultdict(lambda: {}) for _ in text_regexes]
  oie_recounts = [defaultdict(lambda: {}) for _ in oie_regexes]

  # Process text
  lines = []
  for file_id, (text_fname, oie_fname) in enumerate(zip(args.text_files, args.oie_files)):
    print(f'Processing {text_fname} and {oie_fname}', file=sys.stderr)
    with open(text_fname, 'r') as text_f, open(oie_fname, 'r') as oie_f:
      for line_id, (text_line, oie_line) in tqdm.tqdm(enumerate(zip(text_f, oie_f))):
        text_split = text_line.split('\t')
        json_fname = args.raw_data_dir+text_split[0].replace('new_raw_data', '') # a little hacky
        text_line = '\t'.join(text_split[1:])
        extractions = re.sub(oie_span_re, '', oie_line).split('\t')[1:]
        for text_id, (text_rex, text_rec, oie_rex, oie_rec) in enumerate(zip(text_regexes, text_recounts, oie_regexes, oie_recounts)):
          if text_rex:
            text_rex_re, text_rex_cnt, text_rex_type = text_rex
            m = re.search(text_rex_re, text_line)
            if m:
              if text_rex_type == 'yonly':
                vals = [m.group(f'G{i}') for i in range(text_rex_cnt)]
                vals = [x for x in vals if x is not None]
                assert(len(vals) == 1)
                key = vals[0]
              else:
                key = m.group(1)
              text_rec[key][text_line] = (file_id,line_id)
          if oie_rex:
            # Use a heuristic of only keeping the shortest extraction that matches
            best_extraction = None
            for extraction in extractions:
              m = re.search(oie_rex, extraction)
              if m:
                key = extraction.strip().replace('|||', ' | ')
                if not best_extraction or len(best_extraction[0]) > len(key):
                  best_extraction = (key, text_line, file_id, line_id)
            if best_extraction:
              (key, linet, file_id, line_id) = best_extraction
              oie_rec[key][linet] = (file_id,line_id)

  if not os.path.exists(args.html_dir):
      os.makedirs(args.html_dir)
  shutil.copy2('main.css', f'{args.html_dir}/main.css')

  def page_head(title):
    return f'<html><head><link rel="stylesheet" type="text/css" href="main.css"><title>{title}</title></head><body><h1>{title}</h1>'

  def print_results_table(f, title, records, data):
    if not records: return
    print(f'<h2>{title}</h2><table>', file=f)
    res = sorted(list(records.items()), key=lambda x: -len(x[1]))
    for k, v in res:
      l = len(v)
      print(f'<tr><th>{k} {data[5]} (count: {l})</th></tr>', file=f)
      for text in v.keys():
        print(f'<tr><td colspan=2>{text}</td></tr>', file=f)
    print('</table>', file=f)


  with open(f'{args.html_dir}/index.html', 'w') as findex:
    print(page_head('CORD-19 Information Extraction Report')+'<ul>', file=findex)
    for i, (temp_d, text_rex, text_rec, oie_rex, oie_rec) in enumerate(zip(temp_data, text_regexes, text_recounts, oie_regexes, oie_recounts)):
      if text_rex or oie_rex:
        fname = f'report-{i}.html'
        l = (len(text_rec) if text_rec else 0) + (len(oie_rec) if oie_rec else 0)
        print(f'<li><a href="{fname}">{temp_d[2]}</a> ({l} results)</li>', file=findex)
        with open(f'{args.html_dir}/{fname}', 'w') as f:
          print(page_head(temp_d[2]), file=f)
          print('<p><a href="index.html">&lt;&lt; Back to Top</a></p>', file=f)
          print_results_table(f, 'Textual Template Results', text_rec, temp_d)
          print_results_table(f, 'Information Extraction Results', oie_rec, temp_d)
          print('</body></html>', file=f)
    print('</ul></body></html>', file=findex)
