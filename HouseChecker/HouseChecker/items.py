# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class BuildingInfoItem(scrapy.Item):
	building_name = scrapy.Field()
	region_name = scrapy.Field()
	region_detail = scrapy.Field()
	complete_date = scrapy.Field()
	tags = scrapy.Field()
	price = scrapy.Field()
	avail = scrapy.Field()


HouseCheckerMapping = {
	"accountid": None,
	"accountname": None,
	"xzqh": None,  # 行政区划
	"xzqhname": None,
	"cqmc": "region_name",  # 城区名称
	"xqid": None,
	"xqmc": "building_name",  # 小区名称
	"jzmj": "house_area",  # 建筑面积
	#"fwyt": "house_type",  # 房屋用途 0-不限，10-住宅，12-非住宅，13-其他（非住宅）
	"fwyt": None,
	"fwytValue": None,
	"fbzt": None,  # 房本状态
	"gpfyid": "id",  # 挂牌房源ID
	"gpid": "id2",  # 挂牌ID
	"fwtybh": "uid",  # 房屋统一编号，不唯一，SBGOV
	"fczsh": "uid2",  # 房产证审核，应该唯一
	"tygpbh": "uid3",  # 统一挂牌编号
	"wtcsjg": "price",  # 委托出售价格
	"wtdqts": None,  # 委托到期天数？
	"scgpshsj": "hang_date",  # 首次挂牌审核时间
	"cjsj": "agency_date",  # 上交时间
	"mdmc": "agency_company",  # 中介名称
	"wtxybh": None,  # 委托协议编号
	"wtxycode": None,
	"gplxrcode": None,  # 挂牌联系人编号
	"gplxrdh": None,  # 挂牌联系人电话
	"gplxrxm": "agency_name",  # 挂牌联系人姓名
	"gpzt": None,  # 挂牌状态
	"gpztValue": None,
	"isnew": None,  # 是否新房源
	"sellnum": None,  # 交易次数
	"qyid": None,  # 企业ID
	"qyzt": None,  # 企业状态
	"gphytgsj": None,  # 挂牌核验通过时间
	"hyid": None,  # 核验ID
	"hyjzsj": None,  # 核验截止时间
	"gisx": None,  # 经度
	"gisy": None,  # 纬度
	"szlc": "",
	"szlcname": "",
	"sqhysj": "",
	"hxs": "",
	"hxt": "",
	"hxw": "",
	"gply": "",
	"dqlc": "",
	"czfs": "",
	"cyrybh": "",
	"cqsj": "",
	"zzcs": "",
}

class HouseCheckerItem(scrapy.Item):
    region_name = scrapy.Field()
    building_name = scrapy.Field()
    house_area = scrapy.Field()
    price = scrapy.Field()
    hang_date = scrapy.Field()
    id = scrapy.Field()
    id2 = scrapy.Field()
    uid = scrapy.Field()
    uid2 = scrapy.Field()
    uid3 = scrapy.Field()
    agency_company = scrapy.Field()
    agency_name = scrapy.Field()
    agency_date = scrapy.Field()
