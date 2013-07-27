#!/bin/bash

python sebnf.py samples/boolean_expression.sebnf src/test01.bexpr.txt output/test01.bexpr.res.xml
python sebnf.py samples/expression.sebnf src/test01.expr.txt output/test01.expr.res.xml
