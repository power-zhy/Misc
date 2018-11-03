# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import os
import re
from io import BytesIO

import scrapy
from scrapy.utils import project
from scrapy.pipelines import files
from news import items
from bs4 import BeautifulSoup
import urlparse


class NewsPipeline(files.FilesPipeline):
	data_dir = project.get_project_settings().get("FILES_STORE", "")
	file_name_noend = r"\/:*?|. "
	file_name_escape = {
		'\\': '_',
		'/': '_',
		'*': '#',
		'|': '-',
		':': '：',
		'?': '？',
		'<': '《',
		'>': '》',
		',': '，',
		'.': '。',
		'"': '\'',
	}
	file_name_regex = re.compile("[{}]".format(''.join(file_name_escape.keys())))
	template_regex = re.compile("{{(\w+)}}")
	
	def __init__(self, *args, **kwargs):
		super(NewsPipeline, self).__init__(*args, **kwargs)
		template_file = os.path.join(self.data_dir, "news.html")
		with open(template_file) as file:
			self.template = file.read()
	
	def check_file_name(self, name):
		name = name.strip()
		while name and name[-1] in self.file_name_noend:
			name = name[:-1]
		name = self.file_name_regex.sub(lambda m: self.file_name_escape[m.group(0)], name)
		return name
	
	def get_dir_name(self, item):
		title = item["title"]
		title = self.check_file_name(title)
		dir_name = "{}_{}".format(item["date"].strftime("%Y%m%d"), title)
		full_dir = os.path.join(item["author"], dir_name)
		return full_dir
	
	def process_item(self, item, spider):
		if isinstance(item, items.NewsItem):
			spider.logger.info("Start processing {} ({}) with {} images.".format(item["url"], item["title"], len(item["images"])))
			dir_name = self.get_dir_name(item)
			super(NewsPipeline, self).process_item(item, spider)
			def get_replace(m):
				key = m.group(1)
				if key == "date":
					return item["date"].strftime("%Y%m%d")
				else:
					return item.get(key, "")
			content = self.template_regex.sub(get_replace, self.template)
			content = BeautifulSoup(content, "lxml").prettify()
			buf = BytesIO(content.encode())
			buf.seek(0)
			path = os.path.join(dir_name, "index.html")
			self.store.persist_file(path, buf, self.spiderinfo)
		return item
	
	def get_media_requests(self, item, info):
		dir_name = self.get_dir_name(item)
		for key, val in item["images"].items():
			key = urlparse.urljoin(item["url"], key)
			yield scrapy.Request(key, meta={"dir":dir_name,"name":val})
	
	def file_path(self, request, response=None, info=None):
		dir_name = request.meta.get("dir", "")
		file_name = request.meta.get("name", "") or request.url.split('/')[-1]
		return os.path.join(dir_name, file_name)
	
	def item_completed(self, results, item, info):
		super(NewsPipeline, self).item_completed(results, item, info)
		info.spider.on_item_complete(item, results)
