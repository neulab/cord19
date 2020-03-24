# CORD-19 Information Aggregator

by [Graham Neubig](http://phontron.com), [Emma Strubell](https://people.cs.umass.edu/~strubell/), [Zhengbao Jiang](http://jzb.vanpersie.cc), [Zi-Yi Dou](https://www.linkedin.com/in/zi-yi-dou-852a8710b/) and others at the [Carnegie Mellon University](http://cmu.edu) [Language Technologies Institute](http://lti.cs.cmu.edu)

[**View the extracted information here**](http://www.phontron.com/misc/cord19_report)


This is a tool to browse answers the scientific literature may provide regarding various questions about the novel coronavirus and COVID-19. Click the questions below to see a list of answers with links to the sources that provided them.

**We are looking for help improving this tool!** If you are familiar with reading the medical literature and could give fine-grained feedback please contact us at gneubig@cs.cmu.edu. Or, if you are a programmer and could help please feel free to contribute to this repository!

## Information extraction script

See the `extraction` directory.

## Docs

* [Datasets doc](https://docs.google.com/spreadsheets/d/1v3NLk_cppHoewQiZb4d4rmYrl6QkUbctntTvpB1X2mk/edit#gid=0)
* [OIE Templates Doc](https://docs.google.com/spreadsheets/d/1vatC9MtcGl3ukv5xqMR7RqQyj23fOtCyp7Qgpt0n0fI/edit?usp=sharing)

## Data extraction

Our data is based on the CORD-19 dataset. Ask the authors of this repository for access if you're interested.

- `text-only/*.oie`
  
  Each line has <sub, rel, obj> triplets extracted from the corresponding sentence in `text-only/*.sent`. Triplets are separated by `\t` and each triplet is of the format `subject|||relation|||object`, e.g. `he#0,2|||'s on#3,8|||outside#13,20`. Subjects, relations, and objects are continuous spans of tokens in the format of `text#start_char,end_char`, e.g. `he#0,2`. Note that `text` of the span might only be a substring of the string spanning from `start_char` to `end_char`.

