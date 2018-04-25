# input - processed text from nodejs
# output - statistics of different sorts


# part1-start = apply rules on slack messages

# please use python3 to run
import sys
import operator
import itertools as it
import math
from textblob import TextBlob as tb

import re

# import nltk
# import nltk.compat

import spacy
nlp = spacy.load('en')

dic_lsp = {}	#0:"why can this not", 1: "can this not ?"}
dic_mypos = {}
matched_rule = {}	#store the position of rules that matched
dic_revert = {}
ruleNegStart = 26
dic_rule_freq = {}

# global for similarities
dic_tfidf_word = {}
dic_sen_similar = {}
dic_tok_similar = {}
dic_com_similar = {}
dic_sen_tfidf = {}


# create all dict that has specific tokens

# question words
QW = {
	"could": 1,
	"can": 1,
	"would": 1,
	"will": 1,
	"do": 1,
	"does": 1,
	"did": 1,
	"wonder": 1,
	"were": 1
}

# wh and h questions words

WHQ = {
	"what": 1,
	"where": 1,
	"how": 1,
	"why": 1,
	"which": 1,
	"whom": 1,
	"whose": 1,
	"wherever": 1,
	"when": 1,
	"who": 1,
	"whether": 1
}

# after words
AW = {
	"that": 1,
	"i": 1,
	"you": 1,
	"it": 1,
	"this": 1,
	"there": 1,
	"they": 1,
	"are": 1,
	"anyone": 1,
	"one": 1,
	"any": 1,
	"anybody": 1,
	"doing": 1,
	"anything": 1,
	"we": 1,
	"someone": 1
}

# problem words
PW = {
	"problem": 1,
	"problems": 1,
	"error": 1,
	"errors": 1,
	"help": 1,
	"issue": 1,
	"issues": 1,
	"question": 1,
	"questions": 1,
}

# past myself words
PMW = {
	"am": 1
}

# opposite words
OW = {
	"cant": 1,
	"not": 1
}

# micellious words
MW = {
	"getting": 1,
	"having": 1,
	"outputting": 1,
}

# intermediate words
IW = {
	"is": 1,
	"are": 1,
	"so": 1,                            
	"you": 1,
	"but": 1,                                
	"any": 1,
	"if": 1,
	"have": 1,
	"had": 1,
	"has": 1
}

IW.update(WHQ)
IW.update(PW)

PUNC = {
"!": 1,
".": 1,
# ",": 1
}

MYPOS = {
	"QW": QW,
	"IW": IW,
	"MW": MW,
	"OW": OW,
	"AW": AW,
	"WHQ": WHQ,
	"PW": PW,
	"PMW": PMW,
	"PUNC" : PUNC
}


rule = {
	1: [["?"]],		
	2: [["QW"], ["AW"]],	#<SCORE = 5/6>
	# 3: [["IW"],["PUNC"]],	#3 and 4 quite similar here!	
	# 4: [["WHQ"],["PUNC"]],		
	5: [["WHQ"],["QW"]],		#<SCORE = 3/6> but gets qs when no other indicators are present, very good
	6: [["WHQ"],["VBD"]],		#<SCORE = 4/6>
	7: [["PW"],["PMW"]],
	8: [["PW"],["have"]],
	9: [["have"], ["PW"]],
	10: [["have"], ["DT"], ["PW"]],
	11: [["any"], ["idea"]],
	12: [["is"], ["NN"]],
	13: [["is"],["there","this","that"]],
	14: [["are"], ["there","you","those","these"]],	#<SCORE = 1/2>
	15: [["are"], ["NN"]],
	16: [["were"], ["there","you","those","these"]],
	# 16: [["are"],["VB","VBD","VBG","VBN","VBP","VBZ"]],
	17: [["but"], ["QW"], ["AW"]],
	18: [["but"], ["WHQ"], ["QW"]],
	# 18: [["but"], ["IW"]],
	19: [["why"], ["OW"]],
	20: [["why"], ["IW"]],
	21: [["WHQ"], ["to"]],		#<SCORE = 1/5>
	22: [["whether"], ["AW"]],	#<SCORE = 1/1>
	23: [["wonder"], ["IW"]],
	24: [["PW"], ["is"]],
	25: [["PW"], ["are"]],

	# '-' at the start of token specifies that the latter POS cant be in token
	26: [["-", "VBZ"],["WHQ"], ["QW"], ["AW"]],

	# 25: [EOS + is]
	# 26: [EOS + are]
	#27: [SOS + is + AW]
	#[but not (VBZ) + (WH5+H) + (after words) + (question words)]
	# 9:["WHQ", ["at","is","might"]]
	#but no 'is' afterwards in that sentence, or unitl and or any sentence break is seen]
}


def reinit_matched_rule():
	matched_rule.clear()
	for i in rule:
		matched_rule[i] = 0

def clear_invalid_rule():
	for i in rule:
		if matched_rule[i] != -99:
			matched_rule[i] = 0
		elif matched_rule[i] == -99:
			matched_rule[i] = -100

def reinit_dic_revert():
	dic_revert.clear()
	for i in rule:
		dic_revert[i] = True

def init():
	reinit_matched_rule()
	reinit_dic_revert()
	dic_lsp.clear()
	dic_mypos.clear()

c = 4	#stores the number of words to be taken when doing LSP

# processes strings
def processStr(str):
	doc = nlp(str)
	i=0
	docLen = len(doc)
	if docLen >= c:
		for token in doc:
			if(i+c-1 >= docLen):
				break

			# add 1st token
			key = [token]
			# string = token.text
			for j in range(1,c):
				key.append(token.nbor(j))
				
			
			dic_lsp[i] = key
			key = []
			i+=1
	else:
		key=[]
		for token in doc:
				key.append(token)
		dic_lsp[i] = key
	
	# print(dic_lsp[0])


# called if a token doesn't match a pos and follows certain rules, with no neg rule 
def check_isValid_rule(ruleNo,indexAt):
	if len(rule[ruleNo]) > (len(dic_mypos)-indexAt-1):
		matched_rule[ruleNo] = -1
	elif(dic_revert[ruleNo] != False):
		matched_rule[ruleNo] = 0

# called when token matches pos and is used for after processes
def process_validPos(ruleNo,indexAt):
	# print(tokenPos)
	dic_revert[ruleNo] = False
	# print("bbbb")
	if ruleNo >= ruleNegStart:
		rule_len_left = len(rule[ruleNo])-matched_rule[ruleNo]-1
	else:
		# we dont do matched_rule[ruleNo]-1 here as our rule for ruleNo >=24 starts from 1 and not zero
		# this is in the case where neg array is 0th element
		rule_len_left = len(rule[ruleNo])-1-matched_rule[ruleNo]

	if  rule_len_left == 0:
		matched_rule[ruleNo] = -99
		# print("found",ruleNo)
	elif ruleNo >= ruleNegStart and (rule_len_left > c-indexAt):
		matched_rule[ruleNo] = -1
	elif rule_len_left > (c-indexAt-1):	
		matched_rule[ruleNo] = -1
	else:
		matched_rule [ruleNo] += 1

# finds neg index, assuming '-' its always in 0th position in the returned array
def find_negIndex(ruleNo):
	negIndex = -1
	count = 0;
	# find the index with '-', assume theres only 1 in a rule
	for arr in rule[ruleNo]:
		if arr[0] == "-":
			negIndex = count
			break
		count+=1
	# sanity check
	if negIndex == -1:
		print(ruleNo, "is has no '-' in it")

	return negIndex

# called when token doesn't match pos and has neg rule
def check_isValid_ruleNeg(ruleNo,indexAt, tokenPos):
	negIndex = find_negIndex(ruleNo)

	# -1 with ruleNo because it has 1 arr that is neg
	if len(rule[ruleNo])-1 > (len(dic_mypos)-indexAt):
		matched_rule[ruleNo] = -1
		# print("check_isValid_ruleNeg: rule len is greater", tokenPos)

	if(dic_revert[ruleNo] != False):
		l = len(rule[ruleNo][indexAt])
		# check if neg arr pos are present in token
		for each_myPos in rule[ruleNo][negIndex]:
			if matched_rule[ruleNo] >= 0 and each_myPos != "-":
				if each_myPos == rule[ruleNo][0][l-1]:
					lastMyPos = True
				else:
					lastMyPos = False

				lowpos = ""
				if each_myPos.islower():
					lowpos = dic_lsp[word_index][indexAt].orth_

				# if this is valid, then the neg tokens are present. hence we check if the rule can be valid. else ruleNo = -1
				if (each_myPos == lowpos or each_myPos == tokenPos or (tokenPos == "?" and matched_rule[1] == 0)) and dic_revert[ruleNo] != False:
					if len(rule[ruleNo])-1 > (len(dic_mypos)-indexAt-1):
						matched_rule[ruleNo] = -1
						dic_revert[ruleNo] = False
						return True
					else:
						matched_rule[ruleNo] = 0
						dic_revert[ruleNo] = False
						return True
				elif  lastMyPos and dic_revert[ruleNo] == True:
					return False
				else:
					return
					
# called after a neg rule has cleared that neg tokens are not present
def check_afterNeg(ruleNo, indexAt, tokenPos_list):
	if errDisplay:
		print("New List after Neg----",tokenPos_list)

	lastPos = False
	# reinit_dic_revert()
	tokenPos_len = len(tokenPos_list)
	for tokenPos in tokenPos_list:
		if tokenPos == tokenPos_list[tokenPos_len-1]:
			last_tokenPos = True
			if errDisplay > 1:
				print("last tokenpos: ", tokenPos)
		else: 
			last_tokenPos = False

		# for each rule in rule dic, where matched_rule[ruleNo] != -1, go to a rule and...
		if errDisplay:
			print(tokenPos_list)
			print(tokenPos)
			print('before')
			for i in dic_revert:
				print(i ,dic_revert[i])


		if matched_rule[ruleNo] >= 0:
			for each_myPos in rule[ruleNo][matched_rule[ruleNo]]:
				if matched_rule[ruleNo] >= 0:
					l = len(rule[ruleNo][matched_rule[ruleNo]])
					if each_myPos == rule[ruleNo][matched_rule[ruleNo]][l-1]:
						lastMyPos = True
					else:
						lastMyPos = False

					lowpos = ""
					if each_myPos.islower():
						lowpos = dic_lsp[word_index][indexAt].orth_

					if (each_myPos == lowpos or each_myPos == tokenPos or (tokenPos == "?" and matched_rule[1] == 0)) and dic_revert[ruleNo] != False:					
						process_validPos(ruleNo,indexAt)
					elif last_tokenPos and lastMyPos and dic_revert[ruleNo] != False:
						check_isValid_rule(ruleNo,indexAt)
			


# list of MYPOS, [previous rule if any in a form of a list], index number that is being checked
errDisplay = 0
def checkRule(tokenPos_list, indexAt, word_index, SOS, EOS):
    # no rule to exclude. so check all rules, otherwise not check that rule
    # for each MYPOS in mypos_list take a token and match it with a rule
    # for WHQ
    if errDisplay:
    	print("New List----",tokenPos_list)

    # pre-processing
    if SOS:
    	lowpos = dic_lsp[word_index][0].orth_
    	# print("SOS", SOS, "lowpos",lowpos)
    	if lowpos == "is":
    		matched_rule[28] = -99
    	elif lowpos == "are":
    		matched_rule[29] = -99


    reinit_dic_revert()
    tokenPos_len = len(tokenPos_list)
    isNegPresent = False
    last_tokenPos = False
    for tokenPos in tokenPos_list:
    	if tokenPos == tokenPos_list[tokenPos_len-1]:
    		last_tokenPos = True
    		if errDisplay:
	    		print("last tokenpos: ", tokenPos)
    	else: 
    		last_tokenPos = False

    	# for each rule in rule dic, where matched_rule[ruleNo] != -1, go to a rule and...
    	if errDisplay:
	    	print(tokenPos_list)
	    	print(tokenPos)
	    	print('before')
	    	for i in dic_revert:
	    		print(i ,dic_revert[i])


    	for ruleNo in rule:
    		# ...check if the rule at x, with position matched_rule[x] is eqaul to mypos
    		# if true, increment the matched_rule[x]
    		if matched_rule[ruleNo] >= 0:
    			if ruleNo >= ruleNegStart: #for neg rules only
    				#find the neg index...(this part may be ommited if negs are always 1st pos array)
    				negIndex = find_negIndex(ruleNo)
    				# print(negIndex)
    				if negIndex == matched_rule[ruleNo]:
    					if not isNegPresent:
    						isNegPresent = check_isValid_ruleNeg(ruleNo,indexAt, tokenPos)
	    					if not isNegPresent and last_tokenPos:
	    						matched_rule[ruleNo]+=1
	    						# print(matched_rule[ruleNo])
	    						# check the given token pos for matches with negindex+1 as negs are not found
	    						check_afterNeg(ruleNo, indexAt, tokenPos_list)
    				else:
    					for each_myPos in rule[ruleNo][matched_rule[ruleNo]]:
			    			if matched_rule[ruleNo] >= 0:
			    				l = len(rule[ruleNo][matched_rule[ruleNo]])
			    				if each_myPos == rule[ruleNo][matched_rule[ruleNo]][l-1]:
			    					lastMyPos = True
			    				else:
			    					lastMyPos = False

				    			lowpos = ""
				    			if each_myPos.islower():
				    				lowpos = dic_lsp[word_index][indexAt].orth_

				    			if (each_myPos == lowpos or each_myPos == tokenPos or (tokenPos == "?" and matched_rule[1] == 0)) and dic_revert[ruleNo] != False:
				    			# check if rule is completely valid, or partially valid or can't be valid in future
				    				process_validPos(ruleNo,indexAt)

				    			# if false, check if the length of rule will hold if started from next dic_mypos. 
					            # if rule len is more than tokens we have in dic_mypos, then we set -1
				    			elif last_tokenPos and lastMyPos and dic_revert[ruleNo] != False:	#we are using lastMyPos because sometimes, the 1st pos out of may works, but later ones doesnt..
				    			# elif last_tokenPos and dic_revert[ruleNo] != False:				#..so thats why we ensure that last one and it still doesnt match, then we do the elif
				    				# we will loop over the token_list again. so restart process..
				    				#.. in order to check if current token list has neg words
				    				# print(matched_rule[ruleNo], ruleNo)
				    				matched_rule[ruleNo] = 0
				    				last_tokenPos = 0
				    				isNegPresent = 0
					    			# check if neg tokens present in current tokenList
					    			for tPos in tokenPos_list:
					    				if tPos == tokenPos_list[tokenPos_len-1]:
								    		last_tokenPos = True
    									else: 
    										last_tokenPos = False

    									if not isNegPresent:
				    						isNegPresent = check_isValid_ruleNeg(ruleNo,indexAt, tPos)
					    					if not isNegPresent and last_tokenPos:
					    						matched_rule[ruleNo]+=1
					    						check_afterNeg(ruleNo, indexAt, tokenPos_list)
					    						# makesure u get 2 here!
				    				# print("after all", matched_rule[ruleNo])


    			else:
		    		for each_myPos in rule[ruleNo][matched_rule[ruleNo]]:
		    			if matched_rule[ruleNo] >= 0:
		    				l = len(rule[ruleNo][matched_rule[ruleNo]])
		    				if each_myPos == rule[ruleNo][matched_rule[ruleNo]][l-1]:
		    					lastMyPos = True
		    				else:
		    					lastMyPos = False

			    			lowpos = ""
			    			if each_myPos.islower():
			    				lowpos = dic_lsp[word_index][indexAt].orth_

			    			if (each_myPos == lowpos or each_myPos == tokenPos or (tokenPos == "?" and matched_rule[1] == 0)) and dic_revert[ruleNo] != False:
			    			# check if rule is completely valid, or partially valid or can't be valid in future
			    				process_validPos(ruleNo,indexAt)

			    			# if false, check if the length of rule will hold if started from next dic_mypos. 
				            # if rule len is more than tokens we have in dic_mypos, then we set -1
			    			elif last_tokenPos and lastMyPos and dic_revert[ruleNo] != False:	#we are using lastMyPos because sometimes, the 1st pos out of may works, but later ones doesnt..
			    			# elif last_tokenPos and dic_revert[ruleNo] != False:				#..so thats why we ensure that last one and it still doesnt match, then we do the elif
				    			check_isValid_rule(ruleNo,indexAt)
			    				# if has '-' in rule
			    				# if ruleNo >= 24:
	    						# 	check_isValid_ruleNeg(ruleNo,indexAt,tokenPos)
			    				# else:
			    					# not have '-' in rule
		
    	# # post processing
    	# if EOS and last_tokenPos:
    	# 	# c-2 as c-1 gives punc, c-2 gives one before punc
    	# 	# lowpos = dic_lsp[word_index][c-1].orth_
    	# 	# if lowpos == "?":
    	# 	# 	matched_rule[1] = -99
    	# 	# print(indexAt)
    	# 	# print(dic_lsp[0])
    	# 	lowpos = dic_lsp[word_index][len(dic_lsp[word_index])-2].orth_
    	# 	# print("EOS", EOS, "lowpos",lowpos)
    	# 	if lowpos == "is":
    	# 		matched_rule[26] = -99
    	# 	elif lowpos == "are":
    	# 		matched_rule[27] = -99

    	if errDisplay:
	    	print('after')
	    	for i in dic_revert:
	    		print(i ,dic_revert[i])

	    	for matched_index in matched_rule:
	    		print(matched_index ,matched_rule[matched_index])



# fill the global dic_mypos with MYPOS and POS and 
def filldic_mypos(word_index):
	dic_mypos.clear()
	index_words=0;
	for word in dic_lsp[word_index]:
	# for "why", find its MYPOS, tag
		if not word.like_url:
			dic_mypos[index_words] = [word.tag_]

			# if word is ?, give it ? tag
			if word.orth_ == "?":
				d = dic_mypos[index_words]
				d.append("?")
				dic_mypos[index_words] = d
			
			for i in MYPOS:
			# take every MYPOS and check their tokens
				for j in MYPOS[i]:
				# if word was found in one of MYPOS
					if (word.orth_).lower() == j:
						d = dic_mypos[index_words]
						d.append(i)
						dic_mypos[index_words] = d
						break

		index_words+=1


s = {
	# 0: "is this way right is.",
}


def getStringsReady(fileIn):
	fileIn = open(fileIn)
	sen = ""
	key = 0
	tsFlag = 0	#if pflag is used to determine if the word is a ts (slack time)
	backupText = "" 	#this stores text for when we look ahead
	ts = ""
	with fileIn as f:
	  	while True:
		    c = f.read(1)
		    if not c:
		      # print( "End of file")
		      break
		    elif c == "p" or tsFlag:
		    	if tsFlag and c == "\t":
		    		tsFlag = 0
		    		ts = backupText
		    		backupText = ""

		    	elif tsFlag and c != "\t" and (c < "0" or c > "9"):
		    		backupText += c
		    		tsFlag = 0
		    		sen += backupText
		    		backupText = ""

		    	else:
		    		tsFlag = 1
		    		backupText += c


		    elif c == "?" or c == "!" or c == ".":
		    	sen+=c
		    	# sen = ts + sen
		    	# print(ts)
		    	if sen[0] == " ":
		    		sen = sen[1:]
		    	s[key] = ts +"\t"+ sen
		    	sen = ""
		    	key+=1
		    	# print ("Read a character:", c)
		    else:
		    	sen+=c

def part1_lable_staments():	
	fileIn = sys.argv[1]
	fileoutRead = fileIn.replace("formatted","outRead")
	fileoutTech = fileIn.replace("formatted","outTech")
	fileoutTest = fileIn.replace("formatted","outTest")
	EOS = 0
	SOS = 0
	getStringsReady(fileIn)
	with open(fileoutRead,'w') as oread, open(fileoutTech,'w') as otech, open(fileoutTest,'w') as otest:
		for phrase in s:
			# string = s[phrase].split("\t",1)[0]
			# string[0] = ts
			# string[1] = actual line
			otech.write("\n"+s[phrase]+"\t")
			oread.write("\n"+s[phrase]+"\t")
			otest.write("\n"+s[phrase]+"\t")
			isquestion = 0
			init()
			# 1) get dic(words)
			processStr(s[phrase])
			# 2) create dic_mypos for len of dic_mypos[i]
			# in this case we will do it for dic_mypos[0] only
			used = []
			for lsp_index in dic_lsp:
				filldic_mypos(lsp_index)
				
				# 3) get the pattern and add it to respect dic_lsp element.
				for mypos in dic_mypos:
					# check for SOS
					if lsp_index == 0:
						SOS = 1
					else:
						SOS = 0
					# check for EOS
					if len(dic_lsp)-1 == lsp_index:
						EOS = 1
					else:
						EOS = 0
					checkRule(dic_mypos[mypos], mypos, lsp_index, SOS, EOS)
				# get rule number out from matched rule and put append to dic_lsp[lsp_index
		
				for matched_index in matched_rule:
					if matched_rule[matched_index] == -99 and matched_rule[matched_index] != -100 :
						dic_lsp[lsp_index].append(matched_index)
						if not matched_index in used:
							otech.write(str(matched_index)+",")
							used.append(matched_index)

						if not isquestion:
							isquestion = 1
							oread.write("T")		


				# end 4 MYPOS rule check in 1 LSP
				# re initialise matched_rule dictionary
				reinit_matched_rule()
				if errDisplay:
					print("Valid rule cleared...")
				
				if errDisplay:
					for x in dic_mypos:
						print(x, dic_mypos[x])
						# print("Rule: ",s[phrase], "New LSP seq--->", dic_lsp[lsp_index])
						# print("New LSP seq--->", dic_lsp[lsp_index])
						# o.write(dic_lsp[lsp_index])
						# print(dic_lsp[lsp_index])

			# end 1 sentence check
			if not isquestion:
					oread.write("F")

	otest.close()
	oread.close()
	otech.close()
		

# part1-end


# part2-start = find total number of messages, questions and non questions in them

dic_fullSen = {}
dic_senTok = {}

def removePunc(line,forQuestionFile):
	
	line = line.lower()
	line = line.replace('.','')
	line = line.replace(',','')
	line = line.replace('‘','')
	line = line.replace('"','')
	line = line.replace('’','')
	line = line.replace('”','')
	line = line.replace('?','')
	line = line.replace('!','')
	line = line.replace('“','')
	line = line.replace(')','')
	line = line.replace('(','')
	line = line.replace('{','')
	line = line.replace('}','')
	line = line.replace(':','')
	line = line.replace('_','')
	if not forQuestionFile:
		line = line.replace('+','')
		line = line.replace('-','')
		line = line.replace('/','')
		line = line.replace('%','')
		line = line.replace('*','')
		line = line.replace('$','')
		line = line.replace('#','')
		line = line.replace('@','')
		line = line.replace('=','')
		
	return line

def extract_questions_only(line):
	if len(line) >= 1:
		isQuestion = line[-1]
		line = line[:-1]
		# print(isQuestion)
		line = line.split("\t",1)[1]
		# print(line)
		# if len(line) > 1:
		# 	line = line[1]
		# else:
		# 	line = line[0]
		return isQuestion, line
	else:
		return "F",""

def part2_stat_total_lable(stat_out):
	fileIn = sys.argv[1]
	fileIn = fileIn.replace("formatted","outRead")
	fileIn = open(fileIn)
	lines = [i.rstrip('\n') for i in fileIn]

	isQuestion = "F"
	question = ""
	count_msg = 0
	count_q = 0
	count_nq = 0

	for line in lines:
		count_msg += 1
		isQuestion, question = extract_questions_only(line)
		if isQuestion == "T":
			count_q += 1
		else:
			count_nq +=1
	stat_out.write("Total messages read =	" + str(count_msg) + "\n")
	stat_out.write("Total questions read =	" + str(count_q) + "\n")
	stat_out.write("Total statements read =	" + str(count_nq) + "\n\n\n\n")

	fileIn.close()

# part2-end


# part3-start = find highest occuring rules,

def part3_rule_frequency(stat_out):
	fileIn = sys.argv[1]
	fileIn = fileIn.replace("formatted","outTech")
	fileIn = open(fileIn)
	lines = [i.rstrip('\n') for i in fileIn]
	extracted_num = ""

	for key in rule:
		dic_rule_freq[key] = 0

	# for SOS and EOS
	dic_rule_freq[28] = 0
	dic_rule_freq[29] = 0

	for line in lines:
		extract = ""
		for c in reversed(line):
			if c != "\t":
				extract += c
			else:
				break
		# stat_out.write(extract+"\n")

		rule_no = ""
		for c in reversed(extract):
			# print(c, sep=' ', end='', flush=True)
			if c != "," :
				rule_no += c
				
			else:
				if len(rule_no) != 0:
					dic_rule_freq[int(rule_no)] += 1
					rule_no = ""
		# print()




	stat_out.write("Rule Frequency-\n")
	for key in dic_rule_freq:
		stat_out.write(str(key) + ":\t" + str(dic_rule_freq[key]) + "\n")

	stat_out.write("\n")
	fileIn.close()

# part3-end

#part4-start create questions file so server can read it and store in DB

def part4_createQuestionFile():
	fileIn = open(sys.argv[1].replace("formatted","outRead"))
	fileOut = sys.argv[1].replace("formatted","question")

	lines = [i.rstrip('\n') for i in fileIn]
	with open(fileOut,'w') as o:
		for line in lines:
			if len(line)>0:
				if line[-1] == "T":
					line = removePunc(line[:-1],1)
					if(len(line.split()) > 2):
						o.write(line+"\n")

	o.close()
	fileIn.close()

# part4-end




# part5 -starts

def part5_createTFIDF_questionFile():
	fileIn = open(sys.argv[1].replace("formatted","outRead"))
	fileOut = sys.argv[1].replace("formatted","tfidf-question")
	lines = [i.rstrip('\n') for i in fileIn]

	with open(fileOut,'a') as o:
		for line in lines:
			if len(line)>0:
				if line[-1] == "T":
					line = removePunc(line[:-1],1)
					o.write(line+"\n")


	o.close()
	fileIn.close()
	return
#part5-ends




# part6-start = get tfidf scores

def tf(word, blob):

	return blob.words.count(word) / len(blob.words)

# how many of word are there in diff docs
def word_in_total_doc(word, bloblist):
	count = 0
	for blob in bloblist:
		for i in blob.words:
			if word == i:
				count+=1
	return count

def idf(word, bloblist):
	totalLen = 0
	for blob in bloblist:
		totalLen +=len(blob.split())
	return len(bloblist) / (1+word_in_total_doc(word, bloblist))

def tfidf(word, blob, bloblist):
   
    return (tf(word, blob) * idf(word, bloblist))*100

def write_top_similar(arr, topn, name, dic, stat_out):
	count = 1
	# print(dic)
	for i in arr:
		key = i[0]
		stat_out.write(str(count) + ":\t" + str(i[1]) + "\n")
		key = i[0].split()
		key1 = int(key[0])
		key2 = int(key[1])
		# print(key1,key2)
		# print(dic_fullSen[int(key1)])
		# print(dic_fullSen[int(key2)])
		if name == "Token":
			stat_out.write(name + str(count) + ":\t" + str(dic[key1]) + "\n")
			stat_out.write(name + str(count) + ":\t" + str(dic[key2]) + "\n\n")
		else:
			stat_out.write(name + str(count) + ":\t" + dic[key1] + "\n")
			stat_out.write(name + str(count) + ":\t" + dic[key2] + "\n\n")

		count += 1
		if count > topn:
			return



# just get the tfidf scores and save in a file
def part6_getTFIDFscores():
	fileIn = sys.argv[1]
	fileIn = fileIn.replace("formatted","tfidf-question")
	fileIn = open(fileIn)	
	bloblist = []
	lines = [i.rstrip('\n') for i in fileIn]
	for line in lines:
		line = line.split("\t",1)
		if len(line) >= 2:
			bloblist.append(tb(line[1]))

	for i,blob in enumerate(bloblist):
	    for word in blob.words:
	    	word = word.lower()
	    	if not word in dic_tfidf_word:
	    		score = tfidf(word, blob, bloblist)
	    		# print(score,word)
	    		dic_tfidf_word[word] = score

	fileout = sys.argv[1].replace("formatted","tfidf")	    	
	with open(fileout,'w') as o:
		for word in dic_tfidf_word:
			o.write(word + "\t" + str(dic_tfidf_word[word]) + "\n")
	o.close()

	# end tfidf shit

#part6-end



def main():
	# create output file where all stats will be written
	stat_out_name = sys.argv[1]
	stat_out_name = stat_out_name.replace("formatted","stat")

	# do part 1
	part1_lable_staments()

	with open(stat_out_name,'w') as stat_out:
		# do part 2
		part2_stat_total_lable(stat_out)

		# do part 3
		part3_rule_frequency(stat_out)

		# clear memory
		dic_lsp.clear()
		dic_mypos.clear()
		matched_rule.clear()
		dic_revert.clear()
		dic_rule_freq.clear()

		#do part 4
		part4_createQuestionFile()

		# do part 5
		# this file will store all history in a suitable format. so every time new history comes in, it will
		# get appened. and tfidf scores will be recalculated using this entire file.
		part5_createTFIDF_questionFile()

	# do part 6
	# print("going to into tfidf")
	part6_getTFIDFscores()

main()