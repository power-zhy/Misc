# -*- coding: utf-8 -*-
import os
import pickle

import scrapy
from scrapy.utils import project
from news import items
from datetime import datetime


class SocietySpider(scrapy.Spider):
	name = 'society'
	allowed_domains = ['www.wuxiareview.com']
	start_urls = ['https://www.wuxiareview.com/gzmdzst.html']
	data_dir = project.get_project_settings().get("FILES_STORE", "")
	save_file = os.path.join(data_dir, "history.txt")
	tmp_file = os.path.join(data_dir, "news_list.tmp")
	
	def __init__(self, *args, **kwargs):
		super(SocietySpider, self).__init__(*args, **kwargs)
		if not os.path.isdir(self.data_dir):
			os.makedirs(self.data_dir)
		self.history_list = {}
		self.news_list = self.load_tmp_file() or []
		if self.news_list:
			self.logger.info("Temp file found, recoving ...")
			self.save_history()
		self.history_list = self.load_history()
		self.item_count = 0
		self.done_count = 0
		self.is_closed = False
	
	def load_tmp_file(self):
		if not os.path.isfile(self.tmp_file):
			return None
		with open(self.tmp_file, 'rb') as file:
			try:
				return pickle.load(file)
			except:
				return None
	
	def save_tmp_file(self, data):
		with open(self.tmp_file, 'wb') as file:
			pickle.dump(data, file)
	
	def load_history(self):
		if not os.path.isfile(self.save_file):
			return {}
		with open(self.save_file) as file:
			history_list = {}
			for line in file.readlines():
				line = line.strip()
				if not line or line.startswith('#'):
					continue
				url, author, date, stats, title = map(lambda s: s.strip(), line.split('\t'))
				history_list[url] = (author, date, stats, title)
			return history_list
	
	def save_history(self, save_all=False):
		if save_all and self.history_list:
			news_list = ["\t".join((url,) + info) + "\n" for url, info in self.history_list.items()]
		else:
			news_list = ["\t".join(item) + "\n" for item in self.news_list]
			save_all = False
		news_list.sort()
		with open(self.save_file, 'w' if save_all else 'a') as file:
			file.writelines(news_list)
		self.logger.info("{} url history saved.".format(len(news_list)))
		self.news_list = []
		if os.path.exists(self.tmp_file):
			os.remove(self.tmp_file)
	
	def parse(self, response):
		for item in response.xpath("//article//a[@href]")[::-1]:
			title = item.xpath("text()")[0].extract().strip()
			url = response.urljoin(item.xpath("@href")[0].extract())
			history_info = self.history_list.get(url)
			if history_info:
				if history_info[-1] not in title:
					self.logger.error("URL has title '{}', different with history one '{}'.".format(title, history_info[-1]))
				continue
			self.item_count += 1
			yield scrapy.Request(url, self.parse_content, meta={"title":title})
	
	def parse_content(self, response):
		title = response.meta.get("title", "")
		header = response.xpath("//section//header[@class='article-header']")
		article = response.xpath("//section//article[@class='article-content']")
		assert(len(header) == 1)
		assert(len(article) == 1)
		header = header[0]
		article = article[0]
		# get title, date and author
		metas = header.xpath(".//*[@class='article-meta']//span//text()").extract()
		assert(metas[1].strip().startswith("分类"))
		assert(metas[-1].strip().startswith("评论"))
		date = datetime.strptime(metas[0].strip(), "%Y-%m-%d")
		tokens = title.split(":", 1)
		if len(tokens) == 2:
			author, title = map(lambda s: s.strip(), tokens)
		else:
			author = metas[2].strip()
		assert(title in header.xpath(".//*[@class='article-title']//a[@href]/text()")[0].extract())
		# get contents
		end_anchor = article.xpath(".//hr[last()]")
		content = article.extract()
		content = content[:content.rfind(end_anchor[0].extract())] + "</article>"
		# remap images
		image_dict = {}
		image_index = 0
		images = article.xpath(".//img/@src").extract()
		for image in images:
			image = image.strip()
			if not image:
				continue
			if image not in content:
				continue
			if image in image_dict:
				continue
			image_index += 1
			image_name = "{:02d}".format(image_index)
			idx = image.rfind('/')
			if idx > 0:
				image_tmp = image[idx+1:]
			else:
				image_tmp = image
			idx = image_tmp.rfind('.')
			if idx > 0:
				image_name += image_tmp[idx:]
			else:
				image_name += ".jpg"
			image_dict[image] = image_name
			content = content.replace(image, image_name)
		# generate item
		item = items.NewsItem()
		item["url"] = response.request.url
		item["title"] = title
		item["author"] = author
		item["date"] = date
		item["content"] = content
		item["images"] = image_dict
		yield item
	
	def on_item_complete(self, item, results):
		url = item["url"]
		author = item["author"]
		title = item["title"]
		total_count = len(results)
		failures = [res[1] for res in results if not res[0]]
		fail_count = len(failures)
		if fail_count:
			self.logger.warning("{}/{} image download failed in {} ({}:{}).".format(
				fail_count, total_count, url, author, title,
			))
			err_msgs = set([f.getErrorMessage() for f in failures])
			if len(err_msgs) >= 3:
				self.logger.warning("Error messages: \n\t{}".format("\n\t".join(err_msgs)))
			else:
				self.logger.warning("Error messages: {}".format(list(err_msgs)))
		else:
			self.logger.info("Download {} ({}:{}) success with {} images.".format(
				url, author, title, total_count,
			))
		if not fail_count or project.get_project_settings().getbool("ALLOW_IMAGE_ERROR"):
			date = item["date"].strftime("%Y-%m-%d")
			stats = "{:02d}/{:02d}".format(total_count - fail_count, total_count)
			self.news_list.append((url, author, date, stats, title))
			self.history_list[url] = (author, date, stats, title)
			self.save_tmp_file(self.news_list)
		self.done_count += 1
		if self.is_closed and self.done_count >= self.item_count:
			self.save_history()
	
	def closed(self, reason):
		self.is_closed = True
		if self.done_count >= self.item_count:
			self.save_history()
		else:
			import time
			time.sleep(max(1, min(30, 0.1*self.item_count)))  # maybe scrapy's bug, need to wait for all pipeline downloads complete
