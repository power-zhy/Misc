# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NewsItem(scrapy.Item):
	url = scrapy.Field()
	title = scrapy.Field()
	author = scrapy.Field()
	date = scrapy.Field()
	content = scrapy.Field()
	images = scrapy.Field()
	
	def __str__(self):
		return "{} ({}:{})".format(self["url"], self["author"], self["title"])
