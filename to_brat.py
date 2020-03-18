import argparse
import os
import pandas
import math


parser = argparse.ArgumentParser(description='convert csv to BRAT format')
parser.add_argument('--inp', type=str, help='input file')
parser.add_argument('--out', type=str, help='output dir')
args = parser.parse_args()


if not os.path.exists(args.out):
	os.makedirs(args.out)

csv = pandas.read_csv(args.inp)
ids = csv['paper_id']
titles = csv['title']
abstracts = csv['abstract']
texts = csv['text']

for id, title, abstract, text in zip(ids, titles, abstracts, texts):
	with open(os.path.join(args.out, id + '.txt'), 'w') as fout:
		if type(title) is str:
			fout.write('[[ TITLE_START ]]')
			fout.write(title)
			fout.write('[[ TITLE_END ]]')
			fout.write('\n\n')
		if type(abstract) is str:
			fout.write('[[ ABSTRACT_START ]]')
			fout.write(abstract)
			fout.write('[[ ABSTRACT_END ]]')
			fout.write('\n\n')
		if type(text) is str:
			fout.write('[[ TEXT_START ]]')
			fout.write(text)
			fout.write('[[ TEXT_END ]]')
