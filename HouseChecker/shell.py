#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import threading
import pprint
import traceback


py3k = sys.version_info[0] >= 3
if (py3k):
	exec("exec_mix = exec")
	from io import StringIO
else:
	exec("""def exec_mix(code, globals = None, locals = None):
				exec code in globals, locals""")
	from StringIO import StringIO


class SmartPrettyPrinter(pprint.PrettyPrinter):
	def format(self, obj, context, maxlevels, level):
		if (not py3k and isinstance(obj, unicode)):
			return (obj.encode("UTF-8"), True, False)
		if (not py3k and isinstance(obj, str)):
			try:
				obj = obj.decode("GBK").encode("UTF-8")
			except UnicodeDecodeError:
				pass
			return (obj, True, False)
		if (isinstance(obj, str)):
			obj = obj.replace("\\", "\\\\").replace("'", "\\'")
			return ("'" + obj + "'", True, False)
		return pprint.PrettyPrinter.format(self, obj, context, maxlevels, level)

class ThreadStringIO(StringIO):
	def __init__(self, orig):
		StringIO.__init__(self)
		self.thread = threading.current_thread()
		self.orig = orig
	
	def write(self, data):
		thread = threading.current_thread()
		if (thread == self.thread):
			StringIO.write(self, data)
		else:
			self.orig.write(data)

class OutputHooker(object):
	def __init__(self, thread=None):
		self.thread = None
		if (thread):
			if (not isinstance(thread, threading.Thread)):
				self.thread = threading.current_thread()
		self.stdout = sys.stdout
		self.stderr = sys.stderr
		self.buf_out = ThreadStringIO(self.stdout)
		self.buf_err = ThreadStringIO(self.stderr)
	
	def start(self):
		sys.stdout = self.buf_out
		sys.stderr = self.buf_err
	
	def stop(self):
		sys.stdout = self.stdout
		sys.stderr = self.stderr
	
	def __enter__(self):
		self.start()
	
	def __exit__(self, exc_type, exc_value, traceback):
		self.stop()
	
	def getvalue(self, remove_last_endline=False):
		stdout = self.buf_out.getvalue()
		stderr = self.buf_err.getvalue()
		if (remove_last_endline):
			stdout = stdout[:-1]
			stderr = stderr[:-1]
		py3k = sys.version_info[0] >= 3
		if (not py3k and isinstance(stdout, unicode)):
			stdout = stdout.encode("UTF-8")
		if (not py3k and isinstance(stderr, unicode)):
			stderr = stderr.encode("UTF-8")
		return (stdout, stderr)
	
	def close(self):
		self.buf_out.close()
		self.buf_err.close()


def get_input(prompt="--> "):
	''' get input from standard input '''
	if (py3k):
		cmd = input(prompt)
	else:
		cmd = raw_input(prompt)
	cmd = cmd.strip()
	return cmd

def _execute(cmd, global_var={}, local_var={}):
	''' execute command, deal with both expressions and statements '''
	if (not cmd):
		return
	try:
		return eval(cmd, global_var, local_var)
	except SyntaxError:
		try:
			exec_mix(cmd, global_var, local_var)
		except Exception:
			traceback.print_exc()
	except Exception:
		traceback.print_exc()

def execute(cmd, global_var={}, local_var={}):
	''' execute one command and print the result to standard output '''
	ret = _execute(cmd, global_var, local_var)
	if (ret != None):
		print(ret)

def obj_convert(obj):
	''' convert non-serializable object into string '''
	if (isinstance(obj, tuple)):
		return tuple(obj_convert(item) for item in obj)
	elif (isinstance(obj, list)):
		return list(obj_convert(item) for item in obj)
	elif (isinstance(obj, dict)):
		return dict({obj_convert(key):obj_convert(obj[key]) for key in obj})
	elif (not py3k and isinstance(obj, unicode)):
		return obj.encode("UTF-8")
	else:
		return str(obj)

def obj2str(obj):
	''' convert non-ascii object into normal string, to avoid displaying \\xXX or u\\xXXXX '''
	return SmartPrettyPrinter().pformat(obj)

def str2obj(str):
	''' convert string back to object '''
	return eval(str)

def execute_to_string(cmd, global_var={}, local_var={}, return_obj=False):
	''' execute one command and return the result as string tuple (ret, stdout, stderr) '''
	hooker = OutputHooker(True)
	with hooker:
		ret = None
		try:
			if (isinstance(cmd, tuple) or isinstance(cmd, list)):
				func = cmd[0]
				args = cmd[1:]
				ret = func(*args)
			else:
				ret = _execute(cmd, global_var, local_var)
		except Exception:
			traceback.print_exc()
		if (ret == None):
			ret = ""
		elif (return_obj):
			ret = obj_convert(ret)
		else:
			ret = obj2str(ret)
	stdout, stderr = hooker.getvalue(True)  # remove the final new line character
	result = (ret, stdout, stderr)
	hooker.close()
	return result

def interact_once(global_var={}, local_var={}):
	''' interact once '''
	try:
		cmd = get_input()
	except EOFError:
		return
	execute(cmd, global_var, local_var)

def interact_loop(global_var={}, local_var={}):
	''' infinite interact loop, with local variable support '''
	while True:
		try:
			cmd = get_input()
		except EOFError:
			break
		execute(cmd, global_var, local_var)

if __name__ == "__main__":
	interact_loop()
	