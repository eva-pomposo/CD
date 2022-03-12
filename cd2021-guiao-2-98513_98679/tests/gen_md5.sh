#!/bin/sh
rm md5sum.txt
#cp *py ../../chord/tests
md5 -r *py > md5sum.txt
gist -u e0b241b133eecdbffbd930bcf7efb3da md5sum.txt  
