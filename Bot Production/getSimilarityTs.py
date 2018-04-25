import sys
import pymysql
import operator
import itertools as it
import spacy
nlp = spacy.load('en')


queryString = sys.argv[1].lower()
channelName = sys.argv[2]
tableName = sys.argv[3]

# WEIGHT THRESHOLD
sen_threshold = 2.5
lemma_sen_threshold = 23

tok_threshold = 30
lemma_tok_threshold = 3

com_threshold =  45
lemma_com_threshold = 15

sen_tfidf_threshold = 50


# print(queryString,channelName,tableName)
dic_sen_similar = {}
dic_sen_score = {}

dic_tok_similar = {}
dic_tok_score = {}

dic_com_similar = {}
dic_com_score = {}

dic_sen_tfidf = {}
dic_sen_tfidf_score = {}

dic_lemma_sen_similar = {}
dic_lemma_sen_score = {}

dic_lemma_tok_similar = {}
dic_lemma_tok_score = {}


dic_lemma_com_similar = {}
dic_lemma_com_score = {}

dic_tfidf_word = {}
ts_list = []	# a list that will contain only unique ts of similar questions. Hence prevents repeated ts

# Open database connection
def get_db_question():
	db = pymysql.connect("localhost","root","1234","slackfaqproduction" )
	cur = db.cursor()
	cur.execute("select * from "+tableName)
	rows = cur.fetchall()
	db.close()
	return rows

def get_tfidf_scores():
	fileIn = open("tfidf-"+channelName+".txt")
	lines = [i.rstrip('\n') for i in fileIn]
	for line in lines:
		line = line.split("\t")
		dic_tfidf_word[line[0]] = float(line[1])


def get_sentence_tfidf(queryString,tableQuestion):
	weight = 0
	queryString = queryString.split()
	tableQuestion = tableQuestion.split()
	for tok1 in queryString:
		for tok2 in tableQuestion:
			if tok1 == tok2:
				if tok1 in dic_tfidf_word: 
					weight += dic_tfidf_word[tok1]
	return weight		

def extract_sen_tokens(line):
	tokList = []
	doc = nlp(line)
	for word in doc:
		if not word.is_stop and word.orth_ != "?" and word.orth_ != "," and word.orth_ != "." and word.orth_ != "!" and word.orth_ != " " and word.orth_ != "-":
			tokList.append(word.orth_)

	return tokList,doc

def get_token_match_weight(queryString,tableQuestion):
	weight = 0
	matchCount = 0
	queryString,a = extract_sen_tokens(queryString)
	tableQuestion,b = extract_sen_tokens(tableQuestion)
	for tok1 in queryString:
		for tok2 in tableQuestion:
			if tok1 == tok2:
				matchCount+=1
				weight+=1
	if (len(queryString)+len(tableQuestion)-matchCount) == 0:
		return 0
	
	return (weight/(len(queryString)+len(tableQuestion)-matchCount))*100


def get_lemma_token_match_weight(queryString,tableQuestion):
	weight = 0
	matchCount = 0
	sen1, doc1 = extract_sen_tokens(queryString)
	sen2, doc2 = extract_sen_tokens(tableQuestion)

	for tok1 in doc1:
		for tok2 in doc2:
			if tok1.lemma_ == tok2.lemma_:
				matchCount+=1
				weight+=1

	if (len(doc1)+len(tableQuestion)-matchCount) == 0:
		return 0
	return (weight/(len(doc1)+len(tableQuestion)-matchCount))*100


def get_sentence_match_weight(queryString,tableQuestion):
	weight = 0
	matchCount = 0
	queryString = queryString.split()
	tableQuestion = tableQuestion.split()
	for tok1 in queryString:
		for tok2 in tableQuestion:
			if tok1 == tok2:
				matchCount+=1
				weight+=1

	if (len(queryString)+len(tableQuestion)-matchCount) == 0:
		return 0
	return (weight/(len(queryString)+len(tableQuestion)-matchCount))*100

def get_lemma_sentence_match_weight(queryString,tableQuestion):
	weight = 0
	matchCount = 0
	doc1 = nlp(queryString)
	doc2 = nlp(tableQuestion)

	for tok1 in doc1:
		for tok2 in doc2:
			if tok1.lemma_ == tok2.lemma_:
				matchCount+=1
				weight+=1

	if (len(doc1)+len(doc2)-matchCount) == 0:
		return 0
	return (weight/(len(doc1)+len(doc2)-matchCount))*100


def similarities(rows):
	countTok = 0
	countTok_lemma = 0
	countSen = 0
	countSen_lemma = 0
	countCom = 0
	countCom_lemma = 0
	countTfidf = 0

	# compare for similar questions
	for row in rows:
		tableQuestion = row[1]
		ts = row[2]

		# match query using sentence matchin algorithm
		wsen = get_sentence_match_weight(queryString,tableQuestion)/(1+(len(tableQuestion.split())+(len(tableQuestion.split())))/2)
		if wsen >= sen_threshold:
			dic_sen_similar[countSen] = ts+"~"+tableQuestion
			dic_sen_score[countSen] = wsen
			countSen+=1

		# match query using lemma sentence matching algorithm
		wsen_lemma = get_lemma_sentence_match_weight(queryString,tableQuestion)
		if wsen_lemma >= lemma_sen_threshold:
			dic_lemma_sen_similar[countSen_lemma] = ts+"~"+tableQuestion
			dic_lemma_sen_score[countSen_lemma] = wsen_lemma
			countSen_lemma+=1

		# match query using token matchin algorithm
		wtok = get_token_match_weight(queryString,tableQuestion)
		if wtok >= tok_threshold:
			dic_tok_similar[countTok] = ts+"~"+tableQuestion
			dic_tok_score[countTok] = wtok
			countTok+=1

		# match query using lemma token matchin algorithm
		wtok_lemma = get_lemma_token_match_weight(queryString,tableQuestion)
		if wtok_lemma >= lemma_tok_threshold:
			dic_lemma_tok_similar[countTok_lemma] = ts+"~"+tableQuestion
			dic_lemma_tok_score[countTok_lemma] = wtok_lemma
			countTok_lemma+=1

		wcom = (wtok+wsen)/2
		if wcom>= com_threshold:
			dic_com_similar[countCom] = ts+"~"+tableQuestion
			dic_com_score[countCom] = wcom
			countCom += 1

		wcom_lemma = (wtok_lemma+wsen_lemma)/2
		if wcom_lemma>= lemma_com_threshold:
			dic_lemma_com_similar[countCom_lemma] = ts+"~"+tableQuestion
			dic_lemma_com_score[countCom_lemma] = wcom_lemma
			countCom_lemma += 1

		wsen_tfidf = get_sentence_tfidf(queryString, tableQuestion)/(1+(len(tableQuestion.split())+(len(tableQuestion.split())))/2)
		if wsen_tfidf >= sen_tfidf_threshold:
			dic_sen_tfidf[countTfidf] = ts+"~"+tableQuestion
			dic_sen_tfidf_score[countTfidf] = wsen_tfidf
			countTfidf += 1

	# sort sentence and token matches, highest 1st
	sorted_sen_similar = sorted(dic_sen_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_tok_similar = sorted(dic_tok_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_com_similar = sorted(dic_com_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_lemma_sen_similar = sorted(dic_lemma_sen_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_lemma_tok_similar = sorted(dic_lemma_tok_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_lemma_com_similar = sorted(dic_lemma_com_score.items(), key=operator.itemgetter(1), reverse=True)
	sorted_sen_tfidf = sorted(dic_sen_tfidf_score.items(), key=operator.itemgetter(1), reverse=True)

	print("USER QUERY: ",queryString,"\n\n")
	with open("similar-"+channelName+".txt","w") as o:
		if sys.argv[4] == "1" or sys.argv[4] == "all":
			print("Matches found using sentence matching algorithm:\n")
			if len(sorted_sen_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_sen_similar):
				list = dic_sen_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
				
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")
		if sys.argv[4] == "2" or sys.argv[4] == "all":
			print("\nMatches found using lemma sentence matching algorithm:\n")
			if len(sorted_lemma_sen_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_lemma_sen_similar):
				list = dic_lemma_sen_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
					
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")

		if sys.argv[4] == "3" or sys.argv[4] == "all":
			print("Matches found using token matching algorithm:\n")
			if len(sorted_tok_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_tok_similar):
				list = dic_tok_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
				
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")

		if sys.argv[4] == "4" or sys.argv[4] == "all":
			print("Matches found using lemma token matching algorithm:\n")
			if len(sorted_lemma_tok_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_lemma_tok_similar):
				list = dic_lemma_tok_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
					
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")

		if sys.argv[4] == "5" or sys.argv[4] == "all":
			print("Matches found using combine matching algorithm:\n")
			if len(sorted_com_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_com_similar):
				list = dic_com_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
					
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")
		if sys.argv[4] == "6" or sys.argv[4] == "all":
			print("Matches found using lemma combine matching algorithm:\n")
			if len(sorted_lemma_com_similar) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_lemma_com_similar):
				list = dic_lemma_com_similar[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")
				
					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")

		if sys.argv[4] == "7" or sys.argv[4] == "all":
			print("Matches found using sentence tfidf matching algorithm:\n")
			if len(sorted_sen_tfidf) == 0:
				print("N/A","\n")
			for i,row in enumerate(sorted_sen_tfidf):
				list = dic_sen_tfidf[row[0]].split("~")
				score = row[1]
				if score > 0:
					print("Score:",score, "->",list[1],"\n")

					if not list[0] in ts_list and i == 0:
						ts_list.append(list[0])
						o.write(str(list[0])+"\n")



def main():
	get_tfidf_scores()
	rows = get_db_question()
	if len(rows) == 0 and len(rows) == undefined:
		return
	else:
		similarities(rows)

main()