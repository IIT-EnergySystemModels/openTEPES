#!/bin/zsh

PIP=pip3

echo "Executing $PIP install..."
cd ../src

$PIP install --editable .
