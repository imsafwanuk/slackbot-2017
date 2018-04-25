#!/bin/bash          
echo hello world

# run get similarity, arguments: query, channel name, table name, compare algorithm code-> "all/0/1/2/3/4/5/"
python3 getSimilarityTs.py "$@" "all"

# remove the file
rm "question-"$2".txt"

# done with script
echo Done bashing similar questions