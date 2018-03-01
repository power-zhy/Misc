# -*- coding: utf-8 -*-

import time
import itertools
import pprint
from pymongo import MongoClient


class TestStat(object):
	def __init__(self, host, port):
		db_name = "HouseChecker"
		src_col_name = "SecondHandHouse"
		dst_col_name = "SecondHandStat"
		conn = MongoClient(host, port)
		self.src_db = conn[db_name][src_col_name]
		#self.dst_db = conn[db_name][dst_col_name]
		#self.dst_db.ensure_index('building_name', unique=True)
		self.curr_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
	
	def stat(self):
		ignore_region_words = ("·",
			"杭州市", "西湖区", "上城区", "下城区", "江干区", "拱墅区", "滨江区", "萧山区", "余杭区",
			#"杭州", "西湖", "上城", "下城", "江干", "拱墅", "滨江", "萧山", "余杭",
		)
		count = 0
		for house_info in self.src_db.find():
			count += 1
			filter = {"uid":house_info["uid"]}
			for key in ("region_name", "building_name"):
				val = house_info[key]
				for word in ignore_region_words:
					val = val.replace(word, '')
				house_info[key] = val
			self.src_db.replace_one(filter, house_info)
			if count % 100 == 0:
				print(count)
		print(count)


class SecondHandStat(object):
	def __init__(self, host, port):
		db_name = "HouseChecker"
		src_col_name = "SecondHandHouse"
		dst_col_name = "SecondHandStat"
		conn = MongoClient(host, port)
		self.src_db = conn[db_name][src_col_name]
		#self.dst_db = conn[db_name][dst_col_name]
		#self.dst_db.ensure_index('building_name', unique=True)
		self.curr_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
	
	def stat(self):
		building_counts = list(self.src_db.aggregate([{"$sortByCount":"$building_name"}]))
		building_names = [item["_id"] for item in building_counts]
		building_names.sort(key = lambda x: len(x))
		import shell
		shell.interact_loop(globals(), locals())
		name_strips = {}
		for name1, name2 in itertools.combinations(building_names, 2):
			if name1 in name2 and name2 not in name_strips:
				name_strips[name2] = name1
		pprint.pprint(name_strips)

host = "localhost"
port = 27017
stat = SecondHandStat(host, port)
stat.stat()
