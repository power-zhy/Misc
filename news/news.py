# -*- coding: utf-8 -*-

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils import project


process = CrawlerProcess(project.get_project_settings())
process.crawl('society')
process.start()
