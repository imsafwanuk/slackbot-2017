import sys
import re

name = sys.argv[1]
fileIn = open(name)
fileOut = name.replace("retrieve","formatted")
lines = [i.rstrip('\n') for i in fileIn]


def processStr(line):
	s = ""
	linkTag = 0
	userTag = 0
	codeTag = 0
	emojiTag = 0
	dotTag = 0			#for stuff like "i need help..... help" get rid of extra dots
	codeCount = 0
	lineLen = len(line)
	for i,c in enumerate(line):
		# get rid of links
		if line[i] == "<" and i < lineLen-2:
			if line[i+1] == "h":
				linkTag = 1
			elif line[i+1] == "@":
				userTag = 1
		elif line[i] == ">":
			if linkTag and userTag:
				print("WRONG IN USER AND LINK TAG!!!!")
			elif linkTag:
				linkTag = 0
			elif userTag:
				s+=","
				userTag = 0

		# # get rid of emojis
		elif line[i] == ':' and not linkTag and i < lineLen-2:
			if not emojiTag and line[i+1]!=" " :
				emojiTag = 1
			else:
				s+="."
				emojiTag = 0
		elif not linkTag and not userTag and not emojiTag:
			s+=line[i]	

	return s

with open(fileOut,'w') as o:
	for line in lines:
		s = processStr(line)
		if len(s) != 0:
			o.	write(s)
			# print(s, end= "")



