# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import os
import sys
import time
from HouseChecker.items import BuildingInfoItem, HouseCheckerItem
from pymongo import MongoClient


class BasePipeline(object):
	ignore_region_words = (" ", "·",
		#"杭州市", "西湖区", "上城区", "下城区", "江干区", "拱墅区", "滨江区", "萧山区", "余杭区",
		#"杭州", "西湖", "上城", "下城", "江干", "拱墅", "滨江", "萧山", "余杭",
	)
	
	def __init__(self):
		self.db_host = "localhost"
		self.db_port = 27017
		self.db_name = "HouseChecker"
	
	def load_db(self, db, unique_key):
		data = {}
		for item in db.find():
			data[item[unique_key]] = item
		return data
	
	def save_db(self, db, unique_key, data):
		for key, val in data.items():
			db.replace_one({unique_key: key}, val, upsert=True)
	
	def check_changes(self, old_dict, new_dict, keys = None):
		if not keys:
			return None
		changes = {}
		for key in keys:
			old_val = old_dict[key]
			new_val = new_dict[key]
			if old_val != new_val:
				changes[key] = (old_val, new_val)
		return changes


class SecondHandHousePipeline(BasePipeline):
	agency_depend_keys = ("id", "id2", "uid2", "agency_company", "agency_name", "price", "agency_date", "hang_date")
	
	def __init__(self):
		super(SecondHandHousePipeline, self).__init__()
		col_name = "SecondHandHouse"
		self.conn = MongoClient(self.db_host, self.db_port)
		self.db = self.conn[self.db_name][col_name]
		self.db.ensure_index("uid", unique=True)
		self.db.ensure_index("building_name", unique=False)
		self.db.ensure_index("house_area", unique=False)
		self.db.ensure_index("price", unique=False)
		self.curr_date = time.strftime("%Y-%m-%d",time.localtime(time.time()))
		self.db_data = self.load_db(self.db, "uid")
		self.item_counts = [0,0,0]  # total, new, changed
	
	def filter_region(self, val1, val2):
		if val1 == val2:
			return val1
		if val1 in val2:
			return val2
		if val2 in val1:
			return val1
		return val1 if len(val1) > len(val2) else val2
	
	def process_item(self, item, spider):
		if not isinstance(item, HouseCheckerItem):
			return item
		need_filter_keys = {
			"region_name": self.filter_region,
			"building_name": self.filter_region,
			"hang_date": max,
			"price": max,
		}
		house_info = dict(item)
		house_info["uid"] = "{}-{}".format(house_info["uid"], house_info["uid2"])
		house_info["uid2"] = house_info.pop("uid3")
		for key in ("region_name", "building_name"):
			val = house_info[key]
			for word in self.ignore_region_words:
				val = val.replace(word, '')
			house_info[key] = val
		agency_info = {}
		for key in self.agency_depend_keys:
			if key in need_filter_keys:
				agency_info[key] = house_info[key]
			else:
				agency_info[key] = house_info.pop(key)
		primary_key = house_info["uid"]
		old_house_info = self.db_data.get(primary_key)
		if old_house_info:
			for key, func in need_filter_keys.items():
				house_info[key] = func(house_info[key], old_house_info[key])
			changed = False
			agencies = old_house_info.pop("agencies")
			changes = old_house_info.pop("changes")
			keys = house_info.keys() - need_filter_keys.keys()
			change = self.check_changes(old_house_info, house_info, keys)
			if change:
				changes[self.curr_date] = change
				changed = True
			for old_agency_info in agencies:
				if old_agency_info["id"] == agency_info["id"]:
					agency_changed = False
					agency_changes = old_agency_info["changes"]
					change = self.check_changes(old_agency_info, agency_info, self.agency_depend_keys)
					if change:
						agency_changes[self.curr_date] = change
						changed = True
					break
			else:
				agency_info["changes"] = {}
				agencies.append(agency_info)
			house_info["agencies"] = agencies
			house_info["changes"] = changes
			house_info["_check_date"] = self.curr_date
			if changed:
				self.item_counts[2] += 1
		else:
			agency_info["changes"] = {}
			house_info["agencies"] = [agency_info]
			house_info["changes"] = {}
			house_info["_check_date"] = self.curr_date
			self.item_counts[1] += 1
		self.db_data[primary_key] = house_info
		self.item_counts[0] += 1
		return item
	
	def close_spider(self, spider):
		if self.item_counts[0]:
			self.save_db(self.db, "uid", self.db_data)
		self.conn.close()
		if self.item_counts[0]:
			print("SecondHandHousePipeline Done! {}({}) records found, including {} new records and {} changed records".format(len(self.db_data), *self.item_counts))
			path = os.path.join(sys.path[-1], "SecondHandHouse.txt")
			with open(path, 'a') as file:
				file.write("{}\tRecords:{:>6d}\tHouses:{:>6d}\tNew:{:>6d}\tChanged:{:>6d}\n".format(self.curr_date, len(self.db_data), *self.item_counts))


class BuildingInfoPipeline(BasePipeline):
	market_info_keys = ("price", "avail")
	
	def __init__(self):
		super(BuildingInfoPipeline, self).__init__()
		col_name = "BuildingInfo"
		self.conn = MongoClient(self.db_host, self.db_port)
		self.db = self.conn[self.db_name][col_name]
		self.db.ensure_index("building_name", unique=True)
		self.db.ensure_index("region_name", unique=False)
		self.db.ensure_index("complete_date", unique=False)
		self.db.ensure_index("price", unique=False)
		self.curr_date = time.strftime("%Y-%m-%d",time.localtime(time.time()))
		self.db_data = self.load_db(self.db, "building_name")
		self.item_counts = [0,0,0]  # total, new, changed
	
	def process_item(self, item, spider):
		if not isinstance(item, BuildingInfoItem):
			return item
		building_info = dict(item)
		for key in ("region_name", "building_name"):
			val = building_info[key]
			for word in self.ignore_region_words:
				val = val.replace(word, '')
			building_info[key] = val
		building_info["building_name"] = "{}-{}".format(building_info["region_name"], building_info["building_name"])
		market_info = {key: building_info.pop(key) for key in self.market_info_keys}
		primary_key = building_info["building_name"]
		old_building_info = self.db_data.get(primary_key)
		if old_building_info:
			changed = False
			markets = old_building_info.pop("markets")
			changes = old_building_info.pop("changes")
			change = self.check_changes(old_building_info, building_info, building_info.keys())
			if change:
				changes[self.curr_date] = change
				changed = True
			old_market_info = markets[-1]
			change = self.check_changes(old_market_info, market_info, market_info.keys())
			if change:
				market_info["_date"] = self.curr_date
				markets.append(market_info)
				changed = True
			building_info["markets"] = markets
			building_info["changes"] = changes
			if changed:
				self.item_counts[2] += 1
		else:
			market_info["_date"] = self.curr_date
			building_info["markets"] = [market_info]
			building_info["changes"] = {}
			self.item_counts[1] += 1
		self.db_data[primary_key] = building_info
		self.item_counts[0] += 1
		return item
	
	def close_spider(self, spider):
		if self.item_counts[0]:
			self.save_db(self.db, "building_name", self.db_data)
		self.conn.close()
		if self.item_counts[0]:
			print("BuildingInfoPipeline Done! {} records found, including {} new records and {} changed records".format(*self.item_counts))
			path = os.path.join(sys.path[-1], "BuildingInfo.txt")
			with open(path, 'a') as file:
				file.write("{}\tRecords:{:>5d}\tNew:{:>5d}\tChanged:{:>5d}\n".format(self.curr_date, *self.item_counts))
	