#!/usr/bin/env bash

inp_dir=new-text-only
threads=20

set -e

for f in ${inp_dir}/*.sent
do
    # split the file into n pieces
    sp_dir=${f}.sp
    #rm -rf ${f}.sp
    mkdir -p ${sp_dir}
    split -l$((`wc -l < ${f}`/${threads})) ${f} ${sp_dir}/sp -da 5

    # run oie concurrently
    for spf in ${sp_dir}/*
    do
        fout=${spf}.oie
        flog=${spf}.log
        echo "oie/stanford_oie.py --inp $spf --out $fout"
        python oie/stanford_oie.py --inp $spf --out $fout &> $flog &
    done
    wait

    # merge files
    ls -v ${sp_dir}/*.oie | xargs cat > ${f}.oie
done
