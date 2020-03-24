from typing import Iterable, Dict, List, Union
from spacy.lang.en import English
import sys
import os
import json

nlp = English()
sentencizer = nlp.create_pipe("sentencizer")
nlp.add_pipe(sentencizer)

'''
for line in sys.stdin:
  doc = nlp(line.strip())
  for sent in doc.sents:
    print(sent)
'''

def get_text(data: Union[Dict, List, str, int]) -> Iterable[str]:
  if type(data) is dict:
    for k, v in data.items():
      if k == 'text':
        yield v
      else:
        yield from get_text(v)
  elif type(data) is list:
    for v in data:
      yield from get_text(v)
  elif type(data) is str:
    pass
  elif type(data) is int:
    pass
  elif data is None:
    pass
  else:
    raise Exception('not support {}'.format(type(data)))


if __name__ == '__main__':
  root_dir, txt_out, sent_out =sys.argv[1:]
  with open(txt_out, 'w') as text_fout, open(sent_out, 'w') as sent_fout:
    for root, _, files in os.walk(root_dir):
      for file in files:
        file = os.path.join(root, file)
        with open(file, 'r') as fin:
          article = json.load(fin)
          for text in get_text(article):
            text_fout.write('{}\t{}\n'.format(file, text))
            doc = nlp(text.strip())
            for sent in doc.sents:
              sent_fout.write('{}\t{}\n'.format(file, sent))
