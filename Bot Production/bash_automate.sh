#!/bin/bash          
echo hello world
# move retrieve msg from main to process msg
mv "retrieve-"$1 processMessages
# change dir from main to processMessages and process retrieve msg to formatted one
cd processMessages
python3 preprocessMsg.py "retrieve-"$1

# copy formatted file into automate dir
cp "formatted-"$1 ../automate

# go to automate dir and perform question identification and extraction
cd ../automate
python3 automate_questions.py "formatted-"$1

# copy file that contains only question and put it in question folder
cp "question-"$1 ../question

# copy same file to main
cp "question-"$1 ../
cp "tfidf-"$1 ../

# go back to main dir and call updateDB func
cd ..
rm "original-"$1

echo Done bashing

# node -e 'require("./updateDB").init("'$1'")'
