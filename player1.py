import sys
whoareyou = sys.stdin.readline()
print("crayfish")
sys.stdout.flush()
number = 0
while True:
	s = sys.stdin.readline( )
	increment = int(s.strip())
	number += increment
	print(number)
	print("end")
	sys.stdout.flush()
