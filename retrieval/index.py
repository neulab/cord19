from typing import List, Tuple
import argparse
import os
import re
import string
import csv
from tqdm import tqdm
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


PUNCT_TO_SPACE = str.maketrans(string.punctuation, ' ' * len(string.punctuation))


class ESSearcher():
    max_len_query = 1024

    def __init__(self, index_name: str):
        self.es = Elasticsearch()
        self.index_name = index_name

    def query_format(self, query_str: str, field: str):
        new_query_str = query_str.translate(PUNCT_TO_SPACE)
        #new_query_str = ' '.join([w for w in new_query_str.split() if re.match('^[0-9A-Za-z]+$', w)])
        new_query_str = new_query_str.replace(' AND ', ' ').replace(' and ', ' ')
        q = '{}:({})'.format(field, new_query_str[:self.max_len_query])
        return q

    def get_topk(self, query_str: str, field: str, topk: int=5):
        results = self.es.search(
            index=self.index_name,
            q=self.query_format(query_str, field),
            size=topk)['hits']['hits']
        return [(doc['_source'], doc['_score']) for doc in results]


def gendata(files: List[str], index_name: str):
    for file in files:
        with open(file, 'r') as fin:
            for i, l in tqdm(enumerate(fin)):
                yield {
                    '_index': index_name,
                    '_type': 'document',
                    'file': file,
                    'line_id': i,
                    'sentence': l.rstrip('\n')
                }


def retrieve(query: str, index_name: str, topk: int):
    ess = ESSearcher(index_name=index_name)
    results = ess.get_topk(query_str=query, field='sentence', topk=topk)
    return [(r['file'], r['line_id'], r['sentence'], s) for r, s in results]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='index cnndm dataset')
    parser.add_argument('--task', type=str, choices=['index', 'retrieve'], required=True)
    parser.add_argument('--inp', type=str, nargs='+', help='input files')
    parser.add_argument('--out', type=str, help='output dir')
    parser.add_argument('--topk', type=int, help='topk for retrieval', default=1)
    parser.add_argument('--delete', action='store_true')
    args = parser.parse_args()

    index_name = 'cord19'

    if args.task == 'index':
        es = Elasticsearch()
        if args.delete:
            print('delete index')
            es.indices.delete(index=index_name, ignore=[400, 404])
        print('create index')
        print(es.indices.create(index=index_name, ignore=400))
        print('add docs')
        print(bulk(es, gendata(args.inp, index_name=index_name)))

    elif args.task == 'retrieve':
        with open(args.inp[0], 'r') as f:
            csvf = csv.reader(f)
            temp_header = next(csvf)
            temp_data = list(csvf)
            queries = [t[1] for t in temp_data]
        with open(args.out, 'w') as fout:
            for query in tqdm(queries):
                result = retrieve(query, index_name=index_name, topk=args.topk)
                fout.write('** ' + query + '\n')
                for r in result:
                    fout.write('{}\t{}\t{}\n'.format(r[0], r[1], r[2]))
