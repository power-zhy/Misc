#!/usr/bin/python

def hex2int(hex):
	if (hex >= "0") and (hex <= "9"):
		return ord(hex) - ord("0")
	if (hex >= "A") and (hex <= "F"):
		return ord(hex) - ord("A") + 10
	if (hex >= "a") and (hex <= "f"):
		return ord(hex) - ord("a") + 10
	

def str2ipv4(string):
	import re
	string = string.strip()
	result = [0,0,0,0,0]
	match = re.match(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(:(\d{1,5}))?", string)
	if (match):
		for i in range(4):
			result[i] = int(match.group(i+1))
		port = match.group(6)
		if (port):
			result[4] = int(port)
		return result
	match = re.match(r"[0-9A-Fa-f]{8}(:[0-9A-Fa-f]{4})?", string)
	if (match):
		for i in range(4):
			ch1 = string[6-2*i]
			ch2 = string[7-2*i]
			result[i] = hex2int(ch1) * 16 + hex2int(ch2)
		port = match.group(1)
		if (port):
			port = port[1:]
			result[4] = hex2int(port[0]) * (16**3) + hex2int(port[1]) * (16**2) + hex2int(port[2]) * 16 + hex2int(port[3])
		return result
	

if __name__ == "__main__":
	import sys
	if (len(sys.argv) != 2):
		print("Usage: {} ip_str".format(sys.argv[0]))
		exit()
	ip = str2ipv4(sys.argv[1])
	int_format = "{}.{}.{}.{}".format(ip[0], ip[1], ip[2], ip[3]);
	if (ip[4]):
		int_format += ":{}".format(ip[4])
	print("Integer Format: {}".format(int_format))
	