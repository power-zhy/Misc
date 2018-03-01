# -*- coding: utf-8 -*-

import scrapy
import json
import re
from HouseChecker.items import HouseCheckerMapping, HouseCheckerItem

class SecondHandHouseSpider(scrapy.spiders.Spider):
	name = "SecondHandHouse"
	page_regex = re.compile(r"共\s*<[^<>]*>\s*(\d*)\s*<[^<>]*>\s*页")
	
	def __init__(self):
		super(SecondHandHouseSpider, self).__init__()
		self.curr_page = 0
		self.item_counts = [0,0,0]  # total, new, changed
		self.page_sum = None
	
	def gen_formdata(self, pid):
		return {
			"gply": "",
			"wtcsjg": "",
			"jzmj": "",
			"ordertype": "",
			"fwyt": "10",
			"hxs": "",
			"havepic": "",
			"xzqh": "",
			"starttime": "",
			"endtime": "",
			"keywords": "",
			"page": str(pid),
			"xqid": "0",
		}
	
	def gen_request(self, pid):
		url = "http://jjhygl.hzfc.gov.cn/webty/WebFyAction_getGpxxSelectList.jspx"
		return scrapy.FormRequest(
			url = url,
			formdata = self.gen_formdata(pid),
			callback = self.parse,
		)
	
	def gen_item(self, info):
		item = HouseCheckerItem()
		unhoped = []
		unknown = []
		for key, val in info.items():
			item_key = HouseCheckerMapping.get(key, False)
			if item_key is None:
				continue
			if item_key is False:
				unhoped.append(key)
				continue
			if not item_key:
				if val:
					unknown.append((key, val))
				continue
			item[item_key] = val
		if unhoped:
			print("Error: Unhoped key found on uid {}: {}".format(item["uid"], unhoped))
		if unknown:
			print("Error: Unknown key found on uid {}: {}".format(item["uid"], unknown))
		return item
	
	def start_requests(self):
		post = self.gen_request(1)
		yield post
	
	def parse(self, response):
		data = json.loads(response.text)
		if self.page_sum is None:
			self.page_sum = int(self.page_regex.search(data["pageinfo"])[1])
			print("Total page count:", self.page_sum)
			for i in range(2, self.page_sum+1):
				yield self.gen_request(i)
		for item in data["list"]:
			self.item_counts[0] += 1
			yield self.gen_item(item)
		self.curr_page += 1
		print("{}/{} page processed ...      ".format(self.curr_page, self.page_sum), end='\r')
		if self.curr_page == self.page_sum:
			print("Done! {} records found, including {} new records and {} changed records".format(*self.item_counts))
	