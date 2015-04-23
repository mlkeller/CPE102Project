#Not part of the project; used for making/refining the design document.

import sys

try:
   fh = open("designdocument.txt", "r")
   wd = open("design.txt", "w")
except:
   print "Error opening the file."
   sys.exit()

for line in fh:
   word_list = line.split()
   word_list.pop(0)
   word_list.pop(0)
   
   word = word_list[0]
   wd.write("    ")
   for character in word:
      if character != "(":
         wd.write(character)
      else:
         wd.write("\n")
         break

fh.close()
wd.close()
