import argparse
from typing import Dict, List, Set
import os
from collections import namedtuple, defaultdict
from tqdm import tqdm
import spacy
import string
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import wget
os.environ['STANFORD_HOME'] = '/lfs/local/0/xren7/zhengbaj/stanford_home'


Span = namedtuple('Span', ['text', 'start', 'end'])
Triple = namedtuple('Triple', ['subject', 'relation', 'object'])
punct = set(list(string.punctuation))
nlp = spacy.load('en_core_web_sm')
stopwords = nlp.Defaults.stop_words


def get_triple_len(triple: Triple):
    l = triple.subject.end - triple.subject.start + \
        triple.relation.end - triple.relation.start + \
        triple.object.end - triple.object.start
    return l


def span_to_str(span: Span):
    return '{}#{},{}'.format(span.text, span.start, span.end)


def str_to_span(string: str) -> Span:
    text, pos = string.rsplit('#', 1)
    s, e = list(map(int, pos.split(',')))
    return Span(text, s, e)


def triples_to_str(triples: List[Triple]):
    return '\t'.join(map(lambda t: '|||'.join(
        [span_to_str(t.subject), span_to_str(t.relation), span_to_str(t.object)]), triples))


def str_to_triples(string: str) -> List[Triple]:
    if len(string) == 0:
        return []
    return [Triple(*[str_to_span(e) for e in t.split('|||')]) for t in string.split('\t')]


class StanfordOpenIE:
    def __init__(self, core_nlp_version: str = '2018-10-05', threads: int = 5, close_after_finish: bool = True):
        self.remote_url = 'http://nlp.stanford.edu/software/stanford-corenlp-full-{}.zip'.format(core_nlp_version)
        self.install_dir = Path(os.environ['STANFORD_HOME']).expanduser()
        self.install_dir.mkdir(exist_ok=True)
        if not (self.install_dir / Path('stanford-corenlp-full-{}'.format(core_nlp_version))).exists():
            print('Downloading to %s.' % self.install_dir)
            output_filename = wget.download(self.remote_url, out=str(self.install_dir))
            print('\nExtracting to %s.' % self.install_dir)
            zf = ZipFile(output_filename)
            zf.extractall(path=self.install_dir)
            zf.close()

        os.environ['CORENLP_HOME'] = str(self.install_dir / 'stanford-corenlp-full-2018-10-05')
        from stanfordnlp.server import CoreNLPClient
        self.close_after_finish = close_after_finish
        self.client = CoreNLPClient(annotators=['openie'], memory='8G', threads=threads)

    def get_openie_with_boundary(self, annotation: Dict, remove_dup: bool = False) -> List[Triple]:
        triples: List[Triple] = []
        dup: Set['unique'] = set()
        for sentence in annotation['sentences']:
            tokens = sentence['tokens']
            for triple in sentence['openie']:
                new_triple = {}
                for field in ['subject', 'relation', 'object']:
                    text = triple[field]
                    s, e = triple[field + 'Span']
                    s = tokens[s]['characterOffsetBegin']
                    e = tokens[e - 1]['characterOffsetEnd']
                    new_triple[field] = Span(text=text, start=s, end=e)
                key = '\t'.join(['{}-{}'.format(new_triple[field].start, new_triple[field].end)
                                 for field in ['subject', 'relation', 'object']])
                if remove_dup and key in dup:
                    continue
                triples.append(Triple(**new_triple))
                dup.add(key)
        return triples

    def annotate(self,
                 text: str,
                 properties_key: str = None,
                 properties: dict = None,
                 simple_format: bool = True,
                 remove_dup: bool = False,
                 max_len: int=15000):
        """
        :param (str | unicode) text: raw text for the CoreNLPServer to parse
        :param (str) properties_key: key into properties cache for the client
        :param (dict) properties: additional request properties (written on top of defaults)
        :param (bool) simple_format: whether to return the full format of CoreNLP or a simple dict.
        :return: Depending on simple_format: full or simpler format of triples <subject, relation, object>.
        """
        if len(text) >= max_len:
            return []
        # https://stanfordnlp.github.io/CoreNLP/openie.html
        core_nlp_output = self.client.annotate(text=text, annotators=['openie'], output_format='json',
                                               properties_key=properties_key, properties=properties)
        if simple_format:
            return self.get_openie_with_boundary(core_nlp_output, remove_dup=remove_dup)
        else:
            return core_nlp_output

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __del__(self):
        if self.close_after_finish:
            self.client.stop()
            del os.environ['CORENLP_HOME']


def filter_relation(relation: str):
    relation = relation.lower()
    toks = relation.split()
    if relation in punct:  # remove punct
        return False
    if relation[0] in punct:  # start with punct
        return False
    if np.all([w in stopwords for w in toks]):  # all tokens are stopwords
        return False
    if len(toks) > 10:  # too long
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='run open ie on a text file')
    parser.add_argument('--task', type=str, choices=['run', 'filter', 'ana'], default='run')
    parser.add_argument('--inp', type=str, help='input file')
    parser.add_argument('--out', type=str, help='output file')
    parser.add_argument('--threads', type=int, help='number of threads for standford nlp', default=5)
    parser.add_argument('--start_server', action='store_true')
    args = parser.parse_args()

    if args.task == 'run':
        if args.start_server:
            with StanfordOpenIE(threads=args.threads, close_after_finish=False) as client:
                client.annotate('dummy test.', remove_dup=True)
            exit(0)

        with open(args.inp, 'r') as fin, open(args.out, 'w') as fout, \
                StanfordOpenIE(threads=args.threads, close_after_finish=True) as client:
            for lid, line in tqdm(enumerate(fin)):
                id, text = line.strip().split('\t')
                triples = client.annotate(text, remove_dup=False)
                fout.write('{}\t{}\n'.format(id, triples_to_str(triples)))

    elif args.task == 'filter':
        with open(args.inp, 'r') as fin, open(args.out, 'w') as fout:
            for l in tqdm(fin):
                id, text = l.rstrip('\n').split('\t', 1)
                triples = sorted(str_to_triples(text), key=lambda t: get_triple_len(t))
                fout.write('{}\t{}\n'.format(id, triples_to_str(triples[:1])))

    elif args.task == 'ana':
        relation2count = defaultdict(lambda: 0)
        with open(args.inp, 'r') as fin:
            for l in fin:
                for t in str_to_triples(l.rstrip('\n')):
                    relation2count[t.relation.text] += 1
        relation2count = list(filter(lambda x: filter_relation(x[0]),
                                     sorted(relation2count.items(), key=lambda x: -x[1])))
        print('#relation {}'.format(len(relation2count)))
        print(relation2count[:5])
        with open(args.out, 'w') as fout:
            for r, c in relation2count:
                fout.write('{}\t{}\n'.format(r, c))
