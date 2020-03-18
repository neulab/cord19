#!/usr/bin/env bash

# create new env
conda create -n cord19 python=3.7
conda activate cord19

# install
pip install -r requirements.txt
conda install -c anaconda openjdk
