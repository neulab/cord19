A place to put cord19 related stuff.

[Datasets doc](https://docs.google.com/spreadsheets/d/1v3NLk_cppHoewQiZb4d4rmYrl6QkUbctntTvpB1X2mk/edit#gid=0)

## Data

- `text-only/*.oie`

  Each line has <sub, rel, obj> triplets extracted from the corresponding sentence in `text-only/*.sent`. Triplets are separated by `\t` and each triplet is of the format `subject|||relation|||object`, e.g. `he#0,2|||'s on#3,8|||outside#13,20`. Subjects, relations, and objects are continuous spans of tokens in the format of `text#start_char,end_char`, e.g. `he#0,2`. Note that `text` of the span might only be a substring of the string spanning from `start_char` to `end_char`.
