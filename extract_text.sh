
# First, download the dataset from Kaggle and unzip
# Need spacy for this

for f in biorxiv_medrxiv comm_use_subset noncomm_use_subset pmc_custom_license; do
  echo "$f"
  grep -R '"text"' 2020-03-13/$f/ | sed 's/.*"text": "//g; s/",$//g' | tee text-only/$f.txt | python sentence_seg.py > text-only/$f.sent
done

