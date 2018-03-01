# -*- coding: utf-8 -*-

import scrapy
import json
import re
from HouseChecker.items import BuildingInfoItem

class LianjiaBuildingInfoSpider(scrapy.spiders.Spider):
	name = "LianjiaBuildingInfo"
	complete_date_regex = re.compile(r"(\d{4})\s*年建成")
	
	def __init__(self):
		super(LianjiaBuildingInfoSpider, self).__init__()
		self.curr_page = 0
		self.page_sum = None
	
	def gen_request(self, pid):
		url = "http://hz.lianjia.com/xiaoqu/pg{}y3".format(pid)
		return scrapy.Request(
			url = url,
			callback = self.parse,
		)
	
	def start_requests(self):
		post = self.gen_request(1)
		yield post
	
	def parse(self, response):
		selector = scrapy.selector.Selector(response)
		if self.page_sum is None:
			meta_data = json.loads(selector.xpath("//div[@page-data]/@page-data").extract()[0])
			self.page_sum = meta_data["totalPage"]
			print("Total page count:", self.page_sum)
			for i in range(2, self.page_sum+1):
				yield self.gen_request(i)
		table = selector.xpath("//ul[@class='listContent']/li")
		for row in table:
			item = BuildingInfoItem()
			item["building_name"] = row.xpath("div[@class='info']/div[@class='title']/a/text()").extract()[0]
			item["region_name"] = row.xpath("div[@class='info']/div[@class='positionInfo']/a[@class='district']/text()").extract()[0]
			item["region_detail"] = row.xpath("div[@class='info']/div[@class='positionInfo']/a[@class='bizcircle']/text()").extract()[0]
			complete_date = row.xpath("div[@class='info']/div[@class='positionInfo']/a[@class='bizcircle']/following::text()").extract()
			item["complete_date"] = self.complete_date_regex.search("".join(complete_date))[1]
			item["tags"] = row.xpath("div[@class='info']/div[@class='tagList']/span/text()").extract()
			item["price"] = row.xpath("descendant::*[@class='totalPrice']/span/text()").extract()[0]
			item["avail"] = row.xpath("descendant::*[@class='totalSellCount']/span/text()").extract()[0]
			yield item
		self.curr_page += 1
		print("{}/{} page processed ...      ".format(self.curr_page, self.page_sum), end='\r')
	