from spacy.lang.en import English
import sys

nlp = English()
sentencizer = nlp.create_pipe("sentencizer")
nlp.add_pipe(sentencizer)

for line in sys.stdin:
  doc = nlp(line.strip())
  for sent in doc.sents:
    print(sent)
