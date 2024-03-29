#!/usr/bin/python3
# -*- coding:utf-8 -*-

import os
import sys
import datetime
import re
import logging
import pickle
import urllib.request
import urllib.parse
import socket
from http import client
from bs4 import BeautifulSoup
from bs4.element import Tag
from bs4.element import NavigableString
from bs4.element import Comment
from configparser import ConfigParser
from PIL import Image


# global variables
config = None
logger = None
urlsrc = None
urlswitch = None


def debug_output(s):
	if (not isinstance(s, str)):
		s = str(s)
	s = s.encode("GBK", "ignore").decode("GBK", "ignore")
	print("[DEBUG] "+ s)

def get_py_path():
	'''\
	Get the path of current running python script.
	Return: str
	'''
	path = os.path.realpath(os.path.abspath(sys.argv[0]))
	if os.path.isdir(path):
		return path
	elif os.path.isfile(path):
		return os.path.dirname(path)
	else:
		return None

def get_absolute_url(url):
	if url.startswith("data:"):
		return url
	if url.startswith("http://http://") or url.startswith("http://https://"):
		url = url[7:]
	elif url.startswith("https://http://") or url.startswith("https://https://"):
		url = url[8:]
	global urlsrc
	if urlsrc is None:
		return url
	url = urllib.parse.urljoin(urlsrc, url)
	res = urllib.parse.urlparse(url)
	path = os.path.normpath(res.path)
	path = path.replace("\\", "/")
	return urllib.parse.urlunparse((res.scheme, res.netloc, path, res.params, res.query, res.fragment))

def switch_url(url):
	global urlswitch
	if urlswitch is None:
		urlswitch = {}
		data = config["NETWORK"]["URLSwitch"]
		if data:
			for switch in data.strip().split(","):
				pair = switch.split("->")
				assert len(pair) == 2, "Config Error!\n  Invalid URL switch '{}'.".format(switch)
				urlswitch[pair[0].strip()] = pair[1].strip()
	for key in urlswitch:
		url = url.replace(key, urlswitch[key])
	return url

def down_url(url, path, override=None, referer=None, hook=None):
	'''\
	Download a web page [url:str] and save to file with [path:str].
	Return: Bool
	'''
	url = get_absolute_url(url)
	url = switch_url(url)
	if override == None:
		override = config["NETWORK"].getboolean("OverrideFile")
	if os.path.isfile(path) and os.path.getsize(path) > 0 and not override:
		logger.info("File {} already exists, skip downloading.".format(path))
		return True
	logger.info("Downloading {} to {} ...".format(url, path))
	refer = config["NETWORK"]["Referer"]
	if referer is not None:
		refer = referer
	elif urlsrc is not None:
		refer = urlsrc
	headers = {"User-Agent": config["NETWORK"]["UserAgent"], "Referer": refer}
	for retry in range(config["NETWORK"].getint("DownloadMaxRetry")):
		try:
			request = urllib.request.Request(url, headers=headers)
			with urllib.request.urlopen(request, timeout=config["NETWORK"].getint("DownloadTimeout")) as url_data:
				data = url_data.read()
				if data and hook:
					data = hook(url, data)
			if data:
				with open(path, "wb") as file_data:
					file_data.write(data)
				return True
		except socket.timeout:
			pass
		except urllib.error.URLError as err:
			if isinstance(err, urllib.error.HTTPError) and err.code == 403 and "Referer" in headers:
				del headers["Referer"]
			else:
				logger.warning("Download URLError: {}".format(str(err)))
		except client.IncompleteRead as err:
			if retry > 0 and url.startswith("https://"):
				url = "http://" + url[8:]
			else:
				logger.warning("Download IncompleteRead: {}".format(str(err)))
	logger.error("Download {} to {} failed.".format(url, path))
	return False

def parse_html(data):
	result = None
	encode = config["TUGUA"]["SrcEncoding"]
	parser = config["TUGUA"]["HtmlParser"]
	if encode:
		for enc in encode.split():
			try:
				tmp = data.decode(enc)
				tmp = re.subn(r"<\s*br\s*>", "<br />", tmp)[0]  # avoid illegal br tag
				result = BeautifulSoup(tmp, parser)
				logger.info("Decoding success by '{}'".format(enc))
				break
			except Exception as e:
				logger.warning("Try to decode using '{}' failed: {}".format(enc, str(e)))
	if not result:
		result = BeautifulSoup(data, parser)
	return result

def tugua_analyze(tag_src, soup_tmpl, stop_func=None, search_sibling = True):
	'''\
	Analyze tugua at specific node [tag_src:bs4.element.Tag], convert it to a new node with soup template [soup_tmpl:bs4.BeautifulSoup].
	This process stops when [stop_func:(bool)method(tag_src:bs4.element.Tag)] returns True.
	Return: bs4.element.Tag - dest tag converted
	Return: bs4.element.Tag - src tag stopped
	'''
	tag_start = tag_src
	tag_stop = None
	
	def get_obj_size(tag):
		assert isinstance(tag, Tag), "Tag Error!\n  Expect 'tag' but actual is '{}'.".format(tag)
		# other unit to px, using 96dpi and 16px font size
		unit_trans = {
			None: 1,
			"px": 1,
			"em": 16,
			"ex": 8,
			"in": 96,
			"cm": 37.8,
			"mm": 3.78,
			"pt": 1.33,
			"pc": 16,
		}
		width = None
		height = None
		if tag.get("width"):
			width = int(tag.get("width"))
		if tag.get("height"):
			height = int(tag.get("height"))
		style = tag.get("style")
		if not style:
			return (width, height)
		style = style.lower()
		if not width:
			match = re.search(r"(^|[^\w\-])width\s*:\s*(\d+)\s*(px|em|ex|in|cm|mm|pt|pc)?([^\w\-]|$)", style)
			if match:
				number = match.group(2)
				unit = match.group(3)
				width = int(number * unit_trans[unit])
		if not height:
			match = re.search(r"(^|[^\w\-])height\s*:\s*(\d+)\s*(px|em|ex|in|cm|mm|pt|pc)?([^\w\-]|$)", style)
			if match:
				number = match.group(2)
				unit = match.group(3)
				height = int(number * unit_trans[unit])
		return (width, height)
	
	def convert_object(tag):
		assert isinstance(tag, Tag) and (tag.name == "object" or tag.name == "embed"), "Tag Error!\n  Expect 'object' or 'embed' but actual is '{}'.".format(tag)
		for child in tag.children:
			if isinstance(child, Tag) and (child.name == "object" or child.name == "embed"):
				return convert_object(child)
		assert tag.get("type"), "Tag Error!\n  No object type found in '{}'.".format(tag)
		if tag["type"] == "application/x-shockwave-flash":
			(width, height) = get_obj_size(tag)
			if tag.name == "object":
				src = tag.get("data")
			else:
				src = tag.get("src")
			vars = tag.get("flashvars")
			for child in tag.children:
				if isinstance(child, Tag) and child.name == "param":
					name = child.get("name")
					value = child.get("value")
					if not name or not value:
						continue
					name = name.lower()
					if name == "movie" or name == "data" or name == "src":
						src = value
					elif name == "width":
						width = int(value)
					elif name == "height":
						height = int(value)
					elif name == "flashvars":
						vars = vars + "&" + value
			assert src, "Tag Error!\n  Invalid flash url in '{}'.".format(tag)
			if vars:
				if src.find("?") >= 0:
					src = src + "&" + vars
				else:
					src = src + "?" + vars
			result = soup_tmpl.new_tag("embed")
			result["type"] = "application/x-shockwave-flash"
			src = get_absolute_url(src)
			result["src"] = src
			if width:
				result["width"] = width
			if height:
				result["height"] = height
			result["allowFullScreen"] = "true"
			return result
		elif len(tag["type"]) > 6 and tag["type"][:6] == "image/":
			src = tag.get("data")
			for child in tag.children:
				if isinstance(child, Tag) and child.name == "param":
					name = child.get("name")
					value = child.get("value")
					if not value:
						continue
					if name == "movie" or name == "src":
						src = value
			assert src, "Tag Error!\n  Invalid image url in '{}'.".format(tag)
			src = get_absolute_url(src)
			result = soup_tmpl.new_tag("img")
			result["alt"] = ""
			result["src"] = src
			return result
		else:
			logger.warning("Unrecognized object '{}' in '{}'.".format(tag["type"], tag))
			return None
	
	def convert_para(tag):
		assert isinstance(tag, Tag) and (tag.name == "div" or tag.name == "p"), "Tag Error!\n  Expect 'div' or 'p' but actual is '{}'.".format(tag)
		result = tag_convert(tag, ignore_root = True)
		if result:
			result.name = "p"
		return result
	
	def convert_br(tag):
		assert isinstance(tag, Tag) and tag.name == "br", "Tag Error!\n  Expect 'br' but actual is '{}'.".format(tag)
		if tag.contents:
			result = tag_convert(tag, ignore_root = True)
			assert not result.contents, "Tag 'br' should have no contents."
		return soup_tmpl.new_tag("br")
	
	def convert_img(tag):
		assert isinstance(tag, Tag) and tag.name == "img", "Tag Error!\n  Expect 'img' but actual is '{}'.".format(tag)
		src = tag.get("data-src") or tag.get("data-original") or tag.get("src")
		assert src, "Tag Error!\n  Invalid image url in '{}'.".format(tag)
		if src.lower().startswith("file://"):
			return None
		src = get_absolute_url(src)
		result = soup_tmpl.new_tag("img")
		result["alt"] = ""
		result["src"] = src
		return result
	
	def convert_link(tag):
		assert isinstance(tag, Tag) and tag.name == "a", "Tag Error!\n  Expect 'a' but actual is '{}'.".format(tag)
		href = tag.get("href")
		result = tag_convert(tag, ignore_root = True)
		if href and result:
			href = get_absolute_url(href)
			result.name = "a"
			result["href"] = href
		else:
			logger.warning("Unrecognized link in '{}'.".format(tag))
		return result
	
	def convert_table(tag):
		assert isinstance(tag, Tag) and tag.name == "table", "Tag Error!\n  Expect 'table' but actual is '{}'.".format(tag)
		result = soup_tmpl.new_tag("table")
		caption = None
		for child in list(tag.contents):
			if not isinstance(child, Tag):
				continue
			elif child.name == "caption":
				caption = tag_convert(child, ignore_root = True)
				caption.name = child.name
			elif child.name == "tr":
				row = soup_tmpl.new_tag("tr")
				for ch in list(child.contents):
					if not isinstance(ch, Tag):
						continue
					if ch.name == "th" or ch.name == "td":
						item = tag_convert(ch, ignore_root = True)
						item.name = ch.name
						row.append(item)
				result.append(row)
		if caption:
			result.insert(0, caption)
		return result
	
	def convert_frame(tag):
		assert isinstance(tag, Tag) and tag.name == "iframe", "Tag Error!\n  Expect 'iframe' but actual is '{}'.".format(tag)
		(width, height) = get_obj_size(tag)
		src = tag.get("data-src") or tag.get("data-original") or tag.get("src")
		if re.match(config["SOURCECONF"]["IframeSrcRegex"], src):
			result = soup_tmpl.new_tag("embed")
			result["type"] = "application/x-shockwave-flash"
			result["src"] = src
			if width:
				result["width"] = width
			if height:
				result["height"] = height
			result["allowFullScreen"] = "true"
			return result
		elif src:
			src = get_absolute_url(src)
			logger.error("Frame '{}' converted into link.".format(src))
			if config["CORRECTION"].getboolean("PromptOnUnsure"):
				input("Continue? ")
			result = soup_tmpl.new_tag("a")
			result["href"] = src
			result.string = src
			return result
		else:
			logger.warning("Unrecognized frame in '{}'.".format(tag))
			return None
	
	def convert_str(tag):
		assert isinstance(tag, NavigableString), "Tag Error!\n  Expect string but actual is '{}'.".format(tag)
		string = tag.strip()
		string = string.replace("\ufeff", "")
		if string:
			return soup_tmpl.new_string(string)
		else:
			return None
	
	convert_map = {
		"object": convert_object,
		"embed": convert_object,
		"div": convert_para,
		"p": convert_para,
		"br": convert_br,
		"img": convert_img,
		"a": convert_link,
		"table": convert_table,
		"iframe": convert_frame,
	}
	
	def tag_convert(tag, ignore_root = False):
		nonlocal tag_start
		nonlocal tag_stop
		if not tag_start == tag and not tag_start in tag.parents and stop_func and stop_func(tag):
			tag_stop = tag
			return None
		if isinstance(tag, Comment):
			return None
		elif isinstance(tag, NavigableString):
			return convert_str(tag)
		elif not ignore_root and tag.name in convert_map:
			return convert_map[tag.name](tag)
		else:
			result = soup_tmpl.new_tag("")
			for child in list(tag.contents):
				dest = tag_convert(child)
				if dest:
					if isinstance(dest, Tag) and dest.name == "":
						for ch in list(dest.contents):
							result.append(ch)
					else:
						result.append(dest)
				if tag_stop:
					break
			return result
	
	tag_dest = soup_tmpl.new_tag("div")
	while tag_src:
		tag_new = tag_convert(tag_src)
		if tag_new:
			if isinstance(tag_new, Tag) and tag_new.name == "":
				for child in list(tag_new.contents):
					tag_dest.append(child)
			else:
				tag_dest.append(tag_new)
		if not search_sibling or tag_stop:
			break
		while not tag_src.next_sibling and tag_src.parent:
			tag_src = tag_src.parent
		tag_src = tag_src.next_sibling
	return (tag_dest, tag_stop)

def tugua_format(tag_src, soup_tmpl, img_dir="", img_info={}, section_id="", has_subtitle=False):
	'''\
	Format tugua node [tag_src:bs4.element.Tag] to a simple style, with div section [section_id:str] and title when [has_subtitle:bool] is True.
	It also downloads images into [img_dir:str] and renames with "[section_id]_%img_info['count']%.%ext%" or "face_%count%.%ext%", and to avoid duplicated face image, the url of face image will be stored in [img_info:dict].
	It returns a new node with soup template [soup_tmpl:bs4.BeautifulSoup].
	Return: bs4.element.Tag
	'''
	dest = soup_tmpl.new_tag("div")
	if section_id:
		dest["id"] = section_id
	ext_regex = re.compile(r"^data:image/(\w+);|\.(\w+)$|\.(\w+)\?")
	img_format_map = {
		"jpeg": "jpg"
	}
	last_string = ""
	last_para = soup_tmpl.new_tag("p")
	def complete_last_string():
		nonlocal last_string
		nonlocal last_para
		if last_string:
			last_para.append(soup_tmpl.new_string(last_string.strip()))
			last_string = ""
	def complete_last_para():
		nonlocal last_string
		nonlocal last_para
		complete_last_string()
		if last_para.contents:
			dest.append(last_para)
			last_para = soup_tmpl.new_tag("p")
	
	if not tag_src.contents:
		return dest
	for tag in list(tag_src.contents):
		if isinstance(tag, NavigableString):
			last_string += tag.strip()
		elif tag.name == "embed":
			complete_last_para()
			dest.append(tag.wrap(soup_tmpl.new_tag("p")))
		elif tag.name == "img":
			if not config["TUGUA"].getboolean("DownloadImg"):
				complete_last_string()
				last_para.append(tag)
			elif tag["src"] in img_info:
				tag["src"] = img_info[tag["src"]]
				tag["class"] = config["IDENT"]["Face"]
				complete_last_string()
				last_para.append(tag)
			else:
				ext_match = ext_regex.search(tag["src"])
				if ext_match:
					ext = ext_match.group(1) or ext_match.group(2) or ext_match.group(3)
				else:
					logger.warning("No extension found for image '{}', default to '{}'.".format(tag["src"], config["CORRECTION"]["DefaultImgExt"]))
					ext = config["CORRECTION"]["DefaultImgExt"]
				ext = ext.lower()
				if ext in img_format_map:
					ext = img_format_map[ext]
				img_path = os.path.join(img_dir, "{}_{:02}.{}".format(section_id, img_info["count"]+1, ext))
				url = tag["src"].strip()
				if url.startswith("file:"):
					logger.warning("Illegal image url '{}', ignored.".format(url))
				else:
					ret = down_url(url, img_path)
					if not ret:
						input("Continue? ")
					is_face = False
					if ret:
						try:
							img = Image.open(img_path)
							format = img.format
							(img_width, img_height) = img.size
							is_face = img_width <= config["CORRECTION"].getint("FaceImgWidthMax") and img_height <= config["CORRECTION"].getint("FaceImgHeightMax")
							del img
							if format:
								format = format.lower()
							if format in img_format_map:
								format = img_format_map[format]
							if not format:
								logger.error("Can't recognize the format of image '{}'.".format(img_path))
								if config["CORRECTION"].getboolean("PromptOnUnsure"):
									input("Continue? ")
							if format != ext:
								new_img_path = os.path.join(img_dir, "{}_{:02}.{}".format(section_id, img_info["count"]+1, format))
								logger.error("Image format mismatch, Renaming '{}' to '{}'.".format(img_path, new_img_path))
								if config["CORRECTION"].getboolean("PromptOnUnsure"):
									input("Continue? ")
								if os.path.isfile(new_img_path):
									os.remove(new_img_path)
								os.rename(img_path, new_img_path)
								ext = format
								img_path = new_img_path
						except OSError:
							logger.error("Can't recognize image file '{}', default to non-face image.".format(img_path))
							is_face = False
							input("Continue? ")
					if is_face:
						new_img_path = os.path.join(img_dir, "{}_{:02}.{}".format(config["IDENT"]["Face"], len(img_info), ext))
						logger.info("Face image found, Renaming '{}' to '{}'.".format(img_path, new_img_path))
						if os.path.isfile(new_img_path):
							os.remove(new_img_path)
						os.rename(img_path, new_img_path)
						img_path = new_img_path
						img_info[tag["src"]] = img_path
						tag["src"] = img_path
						tag["class"] = config["IDENT"]["Face"]
						complete_last_string()
						last_para.append(tag)
					else:
						img_info["count"] += 1
						tag["src"] = img_path
						complete_last_para()
						dest.append(tag.wrap(soup_tmpl.new_tag("p")))
		elif tag.name == "a":
			temp = tugua_format(tag, soup_tmpl, img_dir=img_dir, img_info=img_info, section_id=section_id)
			link_contents = []
			for child in list(temp.contents):
				for ch in child.contents:
					if isinstance(ch, NavigableString) or (isinstance(ch, Tag) and ch.name == "img" and ch["src"].startswith(config["IDENT"]["Face"])):
						link_contents.append(ch)
					else:
						if link_contents:
							temp = soup_tmpl.new_tag("a")
							temp["href"] = tag["href"]
							for content in link_contents:
								temp.append(content)
							complete_last_string()
							last_para.append(temp)
							link_contents = []
						if isinstance(ch, Tag) and (ch.name == "img" or ch.name == "embed"):
							complete_last_para()
							dest.append(child)
						else:
							assert False, "Content Error!\n  Multiple object found in link '{}'.".format(tag)
				if link_contents:
					temp = soup_tmpl.new_tag("a")
					temp["href"] = tag["href"]
					for content in link_contents:
						temp.append(content)
					complete_last_string()
					last_para.append(temp)
					link_contents = []
		elif tag.name == "p":
			complete_last_para()
			temp = tugua_format(tag, soup_tmpl, img_dir=img_dir, img_info=img_info, section_id=section_id)
			for child in list(temp.contents):
				dest.append(child)
		elif tag.name == "br":
			complete_last_para()
			assert not tag.contents, "Tag 'br' should have no contents."
		else:
			assert False, "Content Error!\n  Unrecognized tag found: '{}'.".format(tag)
	complete_last_para()
	if has_subtitle:
		assert isinstance(dest.contents[0], Tag) and dest.contents[0].name == "p", "Content Error!\n  No subtitle found in section '{}'.".format(tag_src)
		dest.contents[0]["class"] = config["IDENT"]["Subtitle"]
		dest["class"] = config["IDENT"]["Section"]
	return dest

def tugua_srchook(url, data):
	def hook_replace(data, args):
		pair = args.split("->")
		assert len(pair) == 2, "Config Error!\n  Invalid source hook arguments '{}'.".format(args)
		return data.replace(pair[0].strip().encode(encoding="UTF-8"), pair[1].strip().encode(encoding="UTF-8"))
	def hook_regex(data, args):
		pair = args.split("->")
		assert len(pair) == 2, "Config Error!\n  Invalid source hook arguments '{}'.".format(args)
		return re.sub(pair[0].strip().encode(encoding="UTF-8"), pair[1].strip().encode(encoding="UTF-8"), data)

	hook_map = {
		"replace": hook_replace,
		"regex": hook_regex,
	}
	for key, args in config["SOURCEHOOK"].items():
		pair = key.split("@")
		assert len(pair) == 2, "Config Error!\n  Invalid source hook key '{}'.".format(key)
		if pair[0].strip().lower() in url.lower():
			hook_func = hook_map.get(pair[1].strip())
			assert hook_func, "Config Error!\n  Invalid source hook key '{}'.".format(key)
			logger.info("Applying hook to '{}' using '{}' ...".format(url, key))
			data = hook_func(data, args)
	return data

def tugua_download(url, directory="", date=None, orig_url=None):
	'''\
	Download tugua of [date:datetime|str] from [url:str], and store into [directory:str].
	It will create a new folder named "YYYYmmdd" and store converted file into it, and store the original html file into "src" folder.
	Return: None
	'''
	head_regex = re.compile(config["SOURCECONF"]["HeadRegex"])
	tail_regex = re.compile(config["SOURCECONF"]["TailRegex"])
	epi_regex = re.compile(config["SOURCECONF"]["EpilogueRegex"])
	# prepare source directory
	if not date:
		date = datetime.date.today()
	if isinstance(date, datetime.date):
		date_str = date.strftime("%Y%m%d")
	else:
		date_str = date
	directory = os.path.realpath(os.path.abspath(directory))
	src_dir = os.path.join(directory, config["TUGUA"]["SrcDir"])
	if not os.path.isdir(src_dir):
		os.makedirs(src_dir)
	src_path = os.path.join(src_dir, date_str + ".html")
	# download contents
	global urlsrc
	url = url.strip()
	urlsrc = url
	if not down_url(url, src_path, referer="", hook=tugua_srchook):
		input("Continue? ")
	data = None
	with open(src_path, "rb") as src_file:
		data = src_file.read()
	src = parse_html(data)
	dest = BeautifulSoup("", config["TUGUA"]["HtmlParser"])
	# analyze source title and frame
	title_tag_src = src.find("title")
	assert title_tag_src, "No title found!"
	title = title_tag_src.get_text()
	title_match = re.search(r"【喷嚏图卦(\d{8})】\S.*$", title)
	assert title_match, "No title found!\n  Title tag is '{}'.".format(title)
	assert date_str == title_match.group(1), "Date mismatch!\n  Input is '{}', actual is '{}'.".format(date_str, title_match.group(1))
	title = title_match.group(0).strip()
	start_tag_src = src.find(text=head_regex)
	if start_tag_src:
		while not start_tag_src.name or start_tag_src.name == "a":
			start_tag_src = start_tag_src.parent
	end_tag_src = src.find(text=tail_regex)
	if end_tag_src:
		while not end_tag_src.name or end_tag_src.name == "a":
			end_tag_src = end_tag_src.parent
		tmp_tag = end_tag_src.next_sibling
		while tmp_tag:
			if not isinstance(tmp_tag, NavigableString) and tail_regex.match(tmp_tag.get_text()):
				end_tag_src = tmp_tag
			tmp_tag = tmp_tag.next_sibling
	assert start_tag_src and end_tag_src, "No content found!\n  Start is '{}', end is '{}'.".format(start_tag_src, end_tag_src)
	if not end_tag_src.next_element:
		src.append(dest.new_tag("end"))
	# construct dest frame
	dest.append(dest.new_tag("html"))
	head_tag_dest = dest.new_tag("head")
	charset_tag = dest.new_tag("meta")
	charset_tag["http-equiv"] = "Content-Type"
	charset_tag["content"] = "text/html; charset={}".format(config["TUGUA"]["DestEncoding"])
	head_tag_dest.append(charset_tag)
	if config["STYLE"]["JqueryFile"]:
		head_tag_dest.append(dest.new_tag("script", type="text/javascript", src=config["STYLE"]["JqueryFile"]))
	if config["STYLE"]["CssFile"]:
		head_tag_dest.append(dest.new_tag("link", rel="stylesheet", type="text/css", href=config["STYLE"]["CssFile"]))
	if config["STYLE"]["JsFile"]:
		head_tag_dest.append(dest.new_tag("script", type="text/javascript", src=config["STYLE"]["JsFile"]))
	title_tag_dest = dest.new_tag("title")
	title_tag_dest.string = title
	head_tag_dest.append(title_tag_dest)
	dest.html.append(head_tag_dest)
	body_tag_dest = dest.new_tag("body")
	dest.html.append(body_tag_dest)
	# analyze and convert
	subtitle_regex = re.compile(r"^【(\d{0,2})】(.*)")
	def stop_func(tag):
		if tag == end_tag_src:
			return True
		elif not tag or not tag.string:
			return False
		elif subtitle_regex.match(tag.string.strip()):
			return True
		else:
			return False
	(prologue, curr_src) = tugua_analyze(start_tag_src, dest, stop_func=stop_func)
	sections = []
	while True:
		assert curr_src, "Unsupported Error!\n  Analysis tag suspended."
		(section, curr_src) = tugua_analyze(curr_src, dest, stop_func=stop_func)
		sections.append(section)
		if curr_src == end_tag_src:
			(last_tag, _) = tugua_analyze(curr_src, dest, search_sibling=False)
			if last_tag.name == "div":
				last_tag.name = "p"
			section.append(last_tag)  # a bit tricky, append it into previous section
			break
	# debug
	'''debug_output("0: {}".format(prologue))
	count = 0
	for section in sections:
		count += 1
		debug_output("{}: {}".format(count, section))'''
	# check section number
	number_error = 0
	number_count = 0
	number_delta = 0
	for section in sections:
		number_count = number_count + 1
		subtitle = section
		while not isinstance(subtitle, NavigableString):
			subtitle = subtitle.next_element
			assert subtitle, "Content Error!\n  Expect section '{}' but no text found in '{}'.".format(number_count, section)
		subtitle_match = subtitle_regex.match(subtitle)
		assert subtitle_match, "Content Error!\n  Expect subtitle '【{}】' but actual is '{}'.".format(number_count, subtitle)
		curr_id = subtitle_match.group(1)
		if len(curr_id) > 0:
			curr_id = int(curr_id)
		else:
			curr_id = 0
		if curr_id != number_count and curr_id + number_delta != number_count:
			logger.warning("Subtitle number mismatch, expect '{}' but actual is '{}'.".format(number_count, subtitle_match.group(1)))
			number_error = number_error + 1
			number_delta = number_count - curr_id
		subtitle.replace_with(dest.new_string("【{:02}】{}".format(number_count, subtitle_match.group(2).strip())))
	assert number_error <= config["CORRECTION"].getint("TitleNumErrorMax"), "Content Error!\n  Too many subtitle number mismatch, totally {} errors.".format(number_error)
	# prepare destination directory
	dest_dir = os.path.join(directory, date_str)
	if not os.path.isdir(dest_dir):
		os.makedirs(dest_dir)
	os.chdir(dest_dir)
	# load img_info from tmp file
	tmp_path = os.path.join(src_dir, config["TUGUA"]["TmpFile"])
	if os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 0:
		with open(tmp_path, "rb") as tmp_file:
			tmp_data = pickle.loads(tmp_file.read())
	else:
		tmp_data = {}
	if date_str not in tmp_data:
		tmp_data[date_str] = {}
	img_info = tmp_data[date_str]
	img_info["count"] = 0
	# format sections & download images
	try:
		prologue = tugua_format(prologue, dest, img_info=img_info)
		for index in range(len(sections)):
			img_info["count"] = 0
			section = tugua_format(sections[index], dest, img_info=img_info, section_id="{:02}".format(index+1), has_subtitle=True)
			# remove ad
			for tmp_p in list(section.children):
				if re.match(config["SOURCECONF"]["RemoveParaRegex"], tmp_p.text.strip()):
					tmp_p.extract()
			#import shell
			#shell.interact_loop(globals(), locals())
			sections[index] = section
	finally:
		# store img_info into tmp file
		with open(tmp_path, "wb") as tmp_file:
			tmp_data[date_str] = img_info
			tmp_file.write(pickle.dumps(tmp_data))
	# separate extra, ad and epilogue
	tag = sections[-1]
	temp = []
	epi = None
	for child in tag.children:
		ch = child.contents[0]
		if isinstance(ch, Tag) and (ch.name == "img" or ch.name == "embed"):
			temp.clear()
		elif epi_regex.match(child.get_text()):
			epi = child
			break
		else:
			temp.append(child)
	assert epi, "Content Error!\n  No epilogue found in '{}'.".format(tag)
	extra_tag = dest.new_tag("div")
	ad_tag = dest.new_tag("div")
	if temp:
		ad_tmp = temp[-1].extract()
		if len(ad_tmp.contents) == 1 and ad_tmp.contents[0].name == "a" and ad_tmp.contents[0].string.startswith("http") and len(temp) > 1:
			ad_tag.append(temp[-2].extract())
			ad_tag.append(ad_tmp)
			temp = temp[:-2]
		else:
			ad_tag.append(ad_tmp)
			temp = temp[:-1]
		for t in temp:
			extra_tag.append(t.extract())
	epilogue_tag = dest.new_tag("div")
	while epi:
		next_epi = epi.next_sibling
		epilogue_tag.append(epi.extract())
		epi = next_epi
	prologue["id"] = config["IDENT"]["Prologue"]
	prologue["class"] = config["IDENT"]["Prologue"]
	extra_tag["id"] = config["IDENT"]["Extra"]
	extra_tag["class"] = config["IDENT"]["Extra"]
	ad_tag["id"] = config["IDENT"]["Ad"]
	ad_tag["class"] = config["IDENT"]["Ad"]
	epilogue_tag["id"] = config["IDENT"]["Epilogue"]
	epilogue_tag["class"] = config["IDENT"]["Epilogue"]
	# generate title
	title_tag = dest.new_tag("div")
	title_tag["id"] = config["IDENT"]["Title"]
	title_tag["class"] = config["IDENT"]["Title"]
	title_tag.append(dest.new_tag("p"))
	title_tag.p.append(dest.new_tag("a"))
	title_tag.p.a["href"] = orig_url or url
	title_tag.p.a.string = title
	# regroup
	body_tag_dest.append(title_tag)
	body_tag_dest.append(prologue)
	for section in sections:
		body_tag_dest.append(section)
	body_tag_dest.append(extra_tag)
	body_tag_dest.append(ad_tag)
	body_tag_dest.append(epilogue_tag)
	#dest_path = os.path.join(dest_dir, "{}.html".format(title))
	dest_path = os.path.join(dest_dir, config["TUGUA"]["DestFile"])
	with open(dest_path, "wb") as dest_file:
		logger.info("Saving file '{}' ...".format(dest_path))
		dest_file.write(dest.prettify().encode(config["TUGUA"]["DestEncoding"]))
	# delete tmp record when complete
	del tmp_data[date_str]
	with open(tmp_path, "wb") as tmp_file:
		tmp_file.write(pickle.dumps(tmp_data))
	urlsrc = None
	return

def catalogue_analyze(url, directory="", choice=None):
	'''\
	Analyze tugua catalogue page at [url:str] and download all into [directory:str].
	Return int - how many tugua downloaded
	'''
	# prepare directory
	directory = os.path.realpath(os.path.abspath(directory))
	if not os.path.isdir(directory):
		os.makedirs(directory)
	catalog_path = os.path.join(directory, config["TUGUA"]["CatalogFile"])
	if os.path.isfile(catalog_path):
		os.remove(catalog_path)
	# check existing source if choice is specified
	if choice:
		src_dir = os.path.join(directory, config["TUGUA"]["SrcDir"])
		if not os.path.isdir(src_dir):
			os.makedirs(src_dir)
		src_path = os.path.join(src_dir, choice + ".html")
		if os.path.isfile(src_path) and os.path.getsize(src_path) > 0:
			tugua_download("", directory=directory, date=choice)
			return 1
	# download catalogue
	if not down_url(url, catalog_path):
		input("Continue? ")
	with open(catalog_path, "rb") as catalog_file:
		data = catalog_file.read()
		catalog = parse_html(data)
	# find tugua and start downloading
	pre_url = re.search(r"^(\S+/)[^/]*$", url).group(1)
	title_regex = re.compile(r"^【喷嚏图卦(\d{8})】\S.*$")
	min_date = config["TUGUA"]["MinDate"]
	count = 0
	for item in catalog.find_all("a", href=True, text=title_regex):
		href = item["href"]
		title_match = title_regex.match(item.string)
		if not href or not title_match:
			continue
		tugua_title = title_match.group(0).strip()
		tugua_date = title_match.group(1)
		if choice and choice != tugua_date:
			continue
		if min_date and min_date > tugua_date:
			continue
		tugua_dir = os.path.join(directory, tugua_date)
		#tugua_index = os.path.join(tugua_dir, "{}.html".format(tugua_title))
		tugua_index = os.path.join(tugua_dir, config["TUGUA"]["DestFile"])
		if os.path.isdir(tugua_dir) and os.path.isfile(tugua_index):
			continue
		tugua_url = pre_url+href
		logger.info("Start Downloading tugua: {} ({}).".format(tugua_title, tugua_url))
		tugua_download(tugua_url, directory=directory, date=tugua_date)
		count += 1
	return count


if __name__ == "__main__":
	# configuration
	config = ConfigParser()
	cwd = get_py_path()
	os.chdir(cwd)
	config.read("tugua.cfg", encoding="UTF-8")
	# prepare folder
	directory=config["TUGUA"]["TuguaDir"]
	if not os.path.isdir(directory):
		os.makedirs(directory)
	os.chdir(directory)
	# set proxy
	if config["NETWORK"]["DownloadProxy"]:
		os.environ["http_proxy"] = config["NETWORK"]["DownloadProxy"]
	# set logger
	logger = logging.getLogger()
	logger.setLevel(logging.NOTSET)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(formatter)
	handler.setLevel(logging.NOTSET)
	logger.addHandler(handler)
	if config["LOG"]["LogFile"]:
		handler = logging.FileHandler(config["LOG"]["LogFile"])
		handler.setFormatter(formatter)
		handler.setLevel(logging.NOTSET)
		logger.addHandler(handler)
	# check arguments
	if len(sys.argv) > 4:
		logger.fatal("Usage: {} [date_string] [url_string] [orig_url_string]".format(sys.argv[0]))
		exit(1)
	date = None
	url = None
	orig_url = None
	if len(sys.argv) > 3:
		orig_url = sys.argv[3]
		if orig_url.isdigit():
			orig_url = config["TUGUA"]["TuguaURLPrefix"] + orig_url
	if len(sys.argv) > 2:
		url = sys.argv[2]
	if len(sys.argv) > 1:
		date = sys.argv[1]
	# downloading
	try:
		if date and url:
			tugua_download(url, date=date, orig_url=orig_url)
			count = 1
		else:
			count = catalogue_analyze(config["TUGUA"]["CatalogURL"], choice=date)
		logger.info("Totally {} tugua downloaded.".format(count))
	except:
		logger.critical("!!! Exception occurred !!!", exc_info=True)
	logger.info("--------------------------------")
	
