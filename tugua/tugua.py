#!/usr/bin/python
# global variables
config = None
logger = None

def get_py_path():
	'''\
	Get the path of current running python script.
	Return: str
	'''
	import os
	import sys
	path = os.path.realpath(os.path.abspath(sys.argv[0]))
	if os.path.isdir(path):
		return path
	elif os.path.isfile(path):
		return os.path.dirname(path)
	else:
		return None

def down_url(url, path):
	'''\
	Download a web page [url:str] and save to file with [path:str].
	Return: None
	'''
	import os
	import urllib.request
	
	if (os.path.isfile(path)) and (os.path.getsize(path) > 0) and (not config["NETWORK"].getboolean("OverrideFile")):
		logger.info("File {} already exists, skip downloading.".format(path))
		return
	logger.info("Downloading {} to {} ...".format(url, path))
	with urllib.request.urlopen(url, timeout=30) as url_data, open(path, "wb") as file_data:
		file_data.write(url_data.read())
	return

def tugua_analyze(tag_src, soup_tmpl, stop_func=None):
	'''\
	Analyze tugua at specific node [tag_src:bs4.element.Tag], convert it to a new node with soup template [soup_tmpl:bs4.BeautifulSoup].
	This process stops when [stop_func:(bool)method(tag_src:bs4.element.Tag)] returns True.
	Return: bs4.element.Tag - dest tag converted
	Return: bs4.element.Tag - src tag stopped
	'''
	from bs4 import BeautifulSoup
	from bs4.element import Tag
	from bs4.element import NavigableString
	from bs4.element import Comment
	tag_start = tag_src
	tag_stop = None
	
	def get_obj_size(tag):
		assert (isinstance(tag, Tag)), "Tag Error!\n  Expect 'tag' but actual is '{}'.".format(tag)
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
		if (tag.get("width")):
			width = int(tag.get("width"))
		if (tag.get("height")):
			height = int(tag.get("height"))
		style = tag.get("style")
		if (not style):
			return (width, height)
		style = style.lower()
		import re
		if (not width):
			match = re.search(r"(^|[^\w\-])width\s*:\s*(\d+)\s*(px|em|ex|in|cm|mm|pt|pc)?([^\w\-]|$)", style)
			if (match):
				number = match.group(2)
				unit = match.group(3)
				width = int(number * unit_trans[unit])
		if (not height):
			match = re.search(r"(^|[^\w\-])height\s*:\s*(\d+)\s*(px|em|ex|in|cm|mm|pt|pc)?([^\w\-]|$)", style)
			if (match):
				number = match.group(2)
				unit = match.group(3)
				height = int(number * unit_trans[unit])
		return (width, height)
	
	def convert_object(tag):
		assert (tag.name == "object") or (tag.name == "embed"), "Tag Error!\n  Expect 'object' or 'embed' but actual is '{}'.".format(tag)
		for child in tag.children:
			if (child.name == "object") or (child.name == "embed"):
				return convert_object(child)
		assert (tag.get("type")), "Tag Error!\n  No object type found in '{}'.".format(tag)
		if (tag["type"] == "application/x-shockwave-flash"):
			(width, height) = get_obj_size(tag)
			if (tag.name == "object"):
				src = tag.get("data")
			else:
				src = tag.get("src")
			vars = tag.get("flashvars")
			for child in tag.children:
				if (child.name == "param"):
					name = child.get("name")
					value = child.get("value")
					if (not name) or (not value):
						continue
					name = name.lower()
					if (name == "movie") or (name == "data") or (name == "src"):
						src = value
					elif (name == "width"):
						width = int(value)
					elif (name == "height"):
						height = int(value)
					elif (name == "flashvars"):
						vars = vars + "&" + value
			assert (src), "Tag Error!\n  Invalid flash url in '{}'.".format(tag)
			if (vars):
				if (src.find("?") >= 0):
					src = src + "&" + vars
				else:
					src = src + "?" + vars
			result = soup_tmpl.new_tag("embed")
			result["type"] = "application/x-shockwave-flash"
			result["src"] = src
			if (width):
				result["width"] = width
			if (height):
				result["height"] = height
			result["allowFullScreen"] = "true"
			return result
		elif (len(tag["type"]) > 6) and (tag["type"][:6] == "image/"):
			src = tag.get("data")
			for child in tag.children:
				if (child.name == "param"):
					name = child.get("name")
					value = child.get("value")
					if (not value):
						continue
					if (name == "movie") or (name == "src"):
						src = value
			assert (src), "Tag Error!\n  Invalid image url in '{}'.".format(tag)
			result = soup_tmpl.new_tag("img")
			result["alt"] = ""
			result["src"] = src
			return result
		else:
			logger.warn("Unrecognized object '{}' in '{}'.".format(tag["type"], tag))
			return None
	
	def convert_para(tag):
		assert (tag.name == "div") or (tag.name == "p"), "Tag Error!\n  Expect 'div' or 'p' but actual is '{}'.".format(tag)
		result = tag_convert(tag, ignore_root = True)
		if (result):
			result.name = "p"
		return result
	
	def convert_img(tag):
		assert (tag.name == "img"), "Tag Error!\n  Expect 'img' but actual is '{}'.".format(tag)
		src = tag.get("src")
		assert (src), "Tag Error!\n  Invalid image url in '{}'.".format(tag)
		result = soup_tmpl.new_tag("img")
		result["alt"] = ""
		result["src"] = src
		return result
	
	def convert_link(tag):
		assert (tag.name == "a"), "Tag Error!\n  Expect 'a' but actual is '{}'.".format(tag)
		href = tag.get("href")
		result = tag_convert(tag, ignore_root = True)
		if (href) and (result):
			result.name = "a"
			result["href"] = href
		else:
			logger.warn("Unrecognized link in '{}'.".format(tag))
		return result
	
	def convert_table(tag):
		assert (tag.name == "table"), "Tag Error!\n  Expect 'table' but actual is '{}'.".format(tag)
		result = soup_tmpl.new_tag("table")
		caption = None
		for child in list(tag.contents):
			if (child.name == "caption"):
				caption = tag_convert(child, ignore_root = True)
				caption.name = child.name
			elif (child.name == "tr"):
				row = soup_tmpl.new_tag("tr")
				for ch in list(child.contents):
					if (ch.name == "th") or (ch.name == "td"):
						item = tag_convert(ch, ignore_root = True)
						item.name = ch.name
						row.append(item)
				result.append(row)
		if (caption):
			result.insert(0, caption)
		return result
	
	def convert_frame(tag):
		assert (tag.name == "iframe"), "Tag Error!\n  Expect 'iframe' but actual is '{}'.".format(tag)
		(width, height) = get_obj_size(tag)
		src = tag.get("src")
		import re
		if (re.match(r"(https?//)?(\S+\.)?(youku.com|tudou.com|56.com|video.qq.com)/", src)):
			result = soup_tmpl.new_tag("embed")
			result["type"] = "application/x-shockwave-flash"
			result["src"] = src
			if (width):
				result["width"] = width
			if (height):
				result["height"] = height
			result["allowFullScreen"] = "true"
			return result
		elif (src):
			logger.error("Frame '{}' converted into link.".format(src))
			if (config["CORRECTION"].getboolean("PromptOnUnsure")):
				input("Continue? ")
			result = soup_tmpl.new_tag("a")
			result["href"] = src
			result.string = src
			return result
		else:
			logger.warn("Unrecognized frame in '{}'.".format(tag))
			return None
	
	def convert_str(tag):
		assert (isinstance(tag, NavigableString)), "Tag Error!\n  Expect string but actual is '{}'.".format(tag)
		string = tag.strip()
		string = string.replace("\ufeff", "")
		if (string):
			return soup_tmpl.new_string(string)
		else:
			return None
	
	convert_map = {
		"object": convert_object,
		"embed": convert_object,
		"div": convert_para,
		"p": convert_para,
		"img": convert_img,
		"a": convert_link,
		"table": convert_table,
		"iframe": convert_frame,
	}
	
	def tag_convert(tag, ignore_root = False):
		nonlocal tag_start
		nonlocal tag_stop
		if (not tag_start == tag) and (not tag_start in tag.parents) and (stop_func) and stop_func(tag):
			tag_stop = tag
			return None
		if (isinstance(tag, Comment)):
			return None
		elif (isinstance(tag, NavigableString)):
			return convert_str(tag)
		elif (not ignore_root) and (tag.name in convert_map):
			return convert_map[tag.name](tag)
		else:
			result = soup_tmpl.new_tag("")
			for child in list(tag.contents):
				dest = tag_convert(child)
				if (dest):
					if (dest.name == ""):
						for ch in list(dest.contents):
							result.append(ch)
					else:
						result.append(dest)
				if (tag_stop):
					break
			return result
	
	tag_dest = soup_tmpl.new_tag("div")
	while (tag_src):
		tag_new = tag_convert(tag_src)
		if (tag_new):
			if (tag_new.name == ""):
				for child in list(tag_new.contents):
					tag_dest.append(child)
			else:
				tag_dest.append(tag_new)
		if (tag_stop):
			break
		while (not tag_src.next_sibling) and (tag_src.parent):
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
	import re
	from bs4 import BeautifulSoup
	from bs4.element import Tag
	from bs4.element import NavigableString
	
	dest = soup_tmpl.new_tag("div")
	if (section_id):
		dest["id"] = section_id
	ext_regex = re.compile(r"\.(\w+)$")
	img_format_map = {
		"jpeg": "jpg"
	}
	last_string = ""
	last_para = soup_tmpl.new_tag("p")
	def complete_last_string():
		nonlocal last_string
		nonlocal last_para
		if (last_string):
			last_para.append(soup_tmpl.new_string(last_string.strip()))
			last_string = ""
	def complete_last_para():
		nonlocal last_string
		nonlocal last_para
		complete_last_string()
		if (last_para.contents):
			dest.append(last_para)
			last_para = soup_tmpl.new_tag("p")
	
	if (not tag_src.contents):
		return dest
	for tag in list(tag_src.contents):
		if (tag.name == "embed"):
			complete_last_para()
			dest.append(tag.wrap(soup_tmpl.new_tag("p")))
		elif (tag.name == "img"):
			if (not config["TUGUA"].getboolean("DownloadImg")):
				complete_last_string()
				last_para.append(tag)
			elif (tag["src"] in img_info):
				tag["src"] = img_info[tag["src"]]
				tag["class"] = config["IDENT"]["Face"]
				complete_last_string()
				last_para.append(tag)
			else:
				ext_match = ext_regex.search(tag["src"])
				if (ext_match):
					ext = ext_match.group(1)
				else:
					logger.warn("No extension found for image '{}', default to '{}'.".format(tag["src"], config["CORRECTION"]["DefaultImgExt"]))
					ext = config["CORRECTION"]["DefaultImgExt"]
				ext = ext.lower()
				if (ext in img_format_map):
					ext = img_format_map[ext]
				img_path = os.path.join(img_dir, "{}_{:02}.{}".format(section_id, img_info["count"]+1, ext))
				down_url(tag["src"], img_path)
				from PIL import Image
				try:
					img = Image.open(img_path)
					format = img.format
					if (format):
						format = format.lower()
					if (format in img_format_map):
						format = img_format_map[format]
					if (not format):
						logger.error("Can't recognize the format of image '{}'.".format(img_path))
						if (config["CORRECTION"].getboolean("PromptOnUnsure")):
							input("Continue? ")
					if (format != ext):
						new_img_path = os.path.join(img_dir, "{}_{:02}.{}".format(section_id, img_info["count"]+1, format))
						logger.error("Image format mismatch, Renaming '{}' to '{}'.".format(img_path, new_img_path))
						if (config["CORRECTION"].getboolean("PromptOnUnsure")):
							input("Continue? ")
						os.rename(img_path, new_img_path)
						ext = format
						img_path = new_img_path
					(img_width, img_height) = img.size
					is_face = (img_width <= config["CORRECTION"].getint("FaceImgWidthMax")) and (img_height <= config["CORRECTION"].getint("FaceImgHeightMax"))
					del img
				except OSError:
					logger.error("Can't recognize image file '{}', default to non-face image.".format(img_path))
					is_face = False
					input("Continue? ")
				if (is_face):
					new_img_path = os.path.join(img_dir, "{}_{:02}.{}".format(config["IDENT"]["Face"], len(img_info), ext))
					logger.info("Face image found, Renaming '{}' to '{}'.".format(img_path, new_img_path))
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
		elif (tag.name == "a"):
			temp = tugua_format(tag, soup_tmpl, img_dir=img_dir, img_info=img_info, section_id=section_id)
			link_str = False
			for child in list(temp.contents):
				ch = child.contents[0]
				assert (ch.name != "a"), "Content Error!\n  Nested link found in link '{}'.".format(tag)
				if (ch.name == "img") or (ch.name == "embed"):
					complete_last_para()
					dest.append(child)
				else:
					assert (not link_str) and (len(child.contents) == 1) and (isinstance(child.contents[0], NavigableString)), "Content Error!\n  Multiple object found in link '{}'.".format(tag)
					link_str = True
					temp = soup_tmpl.new_tag("a")
					temp["href"] = tag["href"]
					temp.string = soup_tmpl.new_string(child.get_text())
					complete_last_string()
					last_para.append(temp)
			if (not link_str):
				logger.warn("Unrecognized link string in '{}'.".format(tag))
		elif (tag.name == "p"):
			complete_last_para()
			temp = tugua_format(tag, soup_tmpl, img_dir=img_dir, img_info=img_info, section_id=section_id)
			for child in list(temp.contents):
				dest.append(child)
		elif (isinstance(tag, NavigableString)):
			last_string += tag
		else:
			assert (False), "Content Error!\n  Unrecognized tag found: '{}'.".format(tag)
	complete_last_para()
	if (has_subtitle):
		assert (dest.contents[0].name == "p"), "Content Error!\n  No subtitle found in section '{}'.".format(tag_src)
		dest.contents[0]["class"] = config["IDENT"]["Subtitle"]
		dest["class"] = config["IDENT"]["Section"]
	return dest

def tugua_download(url, dir="", date=None):
	'''\
	Download tugua of [date:datetime|str] from [url:str], and store into [dir:str].
	It will create a new folder named "YYYYmmdd" and store converted file into it, and store the original html file into "src" folder.
	Return: None
	'''
	import os
	import re
	import datetime
	from bs4 import BeautifulSoup
	from bs4.element import Tag
	from bs4.element import NavigableString
	
	# prepare source directory
	if (not date):
		date = datetime.date.today()
	if (isinstance(date, datetime.date)):
		date_str = date.strftime("%Y%m%d")
	else:
		date_str = date
	dir = os.path.realpath(os.path.abspath(dir))
	src_dir = os.path.join(dir, config["TUGUA"]["SrcDir"])
	if (not os.path.isdir(src_dir)):
		os.makedirs(src_dir)
	src_path = os.path.join(src_dir, date_str + ".html")
	# download contents
	down_url(url, src_path)
	src = None
	with open(src_path, "rb") as src_file:
		data = src_file.read()
		encode = config["TUGUA"]["SrcEncoding"]
		if (encode):
			for enc in encode.split():
				try:
					src = BeautifulSoup(data.decode(enc))
				except Exception as e:
					logger.warn("Try to decode using '{}' failed: {}".format(enc, str(e)))
		if (not src):
			src = BeautifulSoup(data)
	dest = BeautifulSoup()
	# analyze source title and frame
	title = src.find("title").get_text()
	title_match = re.search(r"【喷嚏图卦(\d{8})】\S.*$", title)
	assert (title_match), "No title found!\n  Title tag is '{}'.".format(title)
	assert (date_str == title_match.group(1)), "Date mismatch!\n  Input is '{}', actual is '{}'.".format(date_str, title_match.group(1))
	title = title_match.group(0).strip()
	start_tag_src = src.find(text=re.compile(r"以下内容，有可能引起内心冲突或愤怒等不适症状。"))
	end_tag_src = src.find(text=re.compile(r"友情提示：请各位河蟹评论。道理你懂的"))
	assert (start_tag_src) and (end_tag_src), "No content found!\n  Start is '{}', end is '{}'.".format(start_tag_src, end_tag_src)
	if (not end_tag_src.next_element):
		src.append(dest.new_tag("end"))
	# construct dest frame
	dest.append(dest.new_tag("html"))
	head_tag_dest = dest.new_tag("head")
	charset_tag = dest.new_tag("meta")
	charset_tag["http-equiv"] = "Content-Type"
	charset_tag["content"] = "text/html; charset={}".format(config["TUGUA"]["DestEncoding"])
	head_tag_dest.append(charset_tag)
	if (config["STYLE"]["JqueryFile"]):
		head_tag_dest.append(dest.new_tag("script", type="text/javascript", src=config["STYLE"]["JqueryFile"]))
	if (config["STYLE"]["CssFile"]):
		head_tag_dest.append(dest.new_tag("link", rel="stylesheet", type="text/css", href=config["STYLE"]["CssFile"]))
	if (config["STYLE"]["JsFile"]):
		head_tag_dest.append(dest.new_tag("script", type="text/javascript", src=config["STYLE"]["JsFile"]))
	title_tag_dest = dest.new_tag("title")
	title_tag_dest.string = title
	head_tag_dest.append(title_tag_dest)
	dest.html.append(head_tag_dest)
	body_tag_dest = dest.new_tag("body")
	dest.html.append(body_tag_dest)
	# analyze and convert
	subtitle_regex = re.compile(r"^【(\d+)】(.*)")
	def stop_func(tag):
		if (not tag) or (not tag.string):
			return False
		if (tag.string == end_tag_src):
			return True
		elif (subtitle_regex.match(tag.string)):
			return True
		else:
			return False
	(prologue, curr_src) = tugua_analyze(start_tag_src, dest, stop_func=stop_func)
	sections = []
	while True:
		assert (curr_src), "Unsupported Error!\n  Analysis tag suspended."
		(section, curr_src) = tugua_analyze(curr_src, dest, stop_func=stop_func)
		sections.append(section)
		if (curr_src) and (curr_src.string == end_tag_src):
			last_tag = dest.new_tag("p")
			last_tag.string = dest.new_string(end_tag_src)
			section.append(last_tag)
			break
	# debug
	'''print("0: {}".format(prologue))
	count = 0
	for section in sections:
		count += 1
		print("{}: {}".format(count, section))'''
	# check section number
	number_error = 0
	number_count = 0
	for section in sections:
		number_count = number_count + 1
		subtitle = section
		while (not isinstance(subtitle, NavigableString)):
			subtitle = subtitle.next_element
			assert (subtitle), "Content Error!\n  Expect section {} but no text found in '{}'.".format(number_count, section)
		subtitle_match = subtitle_regex.match(subtitle)
		assert (subtitle_match), "Content Error!\n  Expect subtitle '【{}】' but actual is '{}'.".format(number_count, subtitle)
		if (int(subtitle_match.group(1)) != number_count):
			logger.warn("Subtitle number mismatch, expect {} but actual is {}.".format(number_count, subtitle_match.group(1)))
			number_error = number_error + 1
		subtitle.replace_with(dest.new_string("【{:02}】{}".format(number_count, subtitle_match.group(2).strip())))
	assert (number_error <= config["CORRECTION"].getint("TitleNumErrorMax")), "Content Error!\n  Too many subtitle number mismatch, totally {} errors.".format(number_error)
	# prepare destination directory
	dest_dir = os.path.join(dir, date_str)
	if (not os.path.isdir(dest_dir)):
		os.makedirs(dest_dir)
	os.chdir(dest_dir)
	# format sections & download images
	img_info = {}
	img_info["count"] = 0
	prologue = tugua_format(prologue, dest, img_info=img_info)
	for index in range(len(sections)):
		img_info["count"] = 0
		sections[index] = tugua_format(sections[index], dest, img_info=img_info, section_id="{:02}".format(index+1), has_subtitle=True)
	# separate extra, ad and epilogue
	tag = sections[len(sections)-1]
	temp = []
	epi_regex = re.compile(r"^来源：\s*喷嚏网\s*综合编辑$")
	for child in tag.children:
		ch = child.contents[0]
		if (ch.name == "img") or (ch.name == "embed"):
			temp.clear()
		elif (epi_regex.match(child.get_text())):
			epi = child
			break
		else:
			temp.append(child)
	assert (epi), "Content Error!\n  No epilogue found in '{}'.".format(tag)
	if (len(temp) != 2):
		logger.error("Extra and ad paragraph are not single in '{}'.".format(temp))
		if (config["CORRECTION"].getboolean("PromptOnUnsure")):
			input("Continue? ")
	extra_tag = dest.new_tag("div")
	for t in temp[:len(temp)-1]:
		extra_tag.append(t.extract())
	ad_tag = dest.new_tag("div")
	ad_tag.append(temp[len(temp)-1].extract())
	epilogue_tag = dest.new_tag("div")
	while(epi):
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
	title_tag.p.a["href"] = url
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
	return

def catalogue_analyze(url, dir=""):
	'''\Analyze tugua catalogue page at [url:str] and download all into [dir:str].
	Return int - how many tugua downloaded
	'''
	import os
	import re
	import datetime
	from bs4 import BeautifulSoup
	
	# prepare directory
	dir = os.path.realpath(os.path.abspath(dir))
	if (not os.path.isdir(dir)):
		os.makedirs(dir)
	catalog_path = os.path.join(dir, config["TUGUA"]["CatalogFile"])
	if (os.path.isfile(catalog_path)):
		os.remove(catalog_path)
	# download catalogue
	down_url(url, catalog_path)
	with open(catalog_path, "rb") as catalog_file:
		data = catalog_file.read()
		encode = config["TUGUA"]["SrcEncoding"]
		if (encode):
			for enc in encode.split():
				try:
					catalog = BeautifulSoup(data.decode(enc))
				except:
					pass
		if (not catalog):
			catalog = BeautifulSoup(data)
	# find tugua and start downloading
	pre_url = re.search(r"^(\S+/)[^/]*$", url).group(1)
	title_regex = re.compile(r"^【喷嚏图卦(\d{8})】\S.*$")
	count = 0
	for item in catalog.find_all("a", href=True, text=title_regex):
		href = item["href"]
		title_match = title_regex.match(item.string)
		if (not href) or (not title_match):
			continue
		tugua_title = title_match.group(0).strip()
		tugua_date = title_match.group(1)
		tugua_dir = os.path.join(dir, tugua_date)
		#tugua_index = os.path.join(tugua_dir, "{}.html".format(tugua_title))
		tugua_index = os.path.join(tugua_dir, config["TUGUA"]["DestFile"])
		if (os.path.isdir(tugua_dir)) and (os.path.isfile(tugua_index)):
			continue
		tugua_url = pre_url+href
		logger.info("Start Downloading tugua: {} ({}).".format(tugua_title, tugua_url))
		tugua_download(tugua_url, dir=dir, date=tugua_date)
		count += 1
	return count


if __name__ == "__main__":
	import os
	import sys
	import datetime
	# configuration
	from configparser import ConfigParser
	config = ConfigParser()
	cwd = get_py_path()
	os.chdir(cwd)
	config.read("tugua.cfg")
	# prepare folder
	dir=config["TUGUA"]["TuguaDir"]
	if (not os.path.isdir(dir)):
		os.makedirs(dir)
	os.chdir(dir)
	# set proxy
	if (config["NETWORK"]["DownloadProxy"]):
		os.environ["http_proxy"] = config["NETWORK"]["DownloadProxy"]
	# set logger
	import logging
	logger = logging.getLogger()
	logger.setLevel(logging.NOTSET)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(formatter)
	handler.setLevel(logging.NOTSET)
	logger.addHandler(handler)
	if (config["LOG"]["LogFile"]):
		handler = logging.FileHandler(config["LOG"]["LogFile"])
		handler.setFormatter(formatter)
		handler.setLevel(logging.NOTSET)
		logger.addHandler(handler)
	# downloading
	try:
		count = catalogue_analyze(config["TUGUA"]["CatalogURL"])
		logger.info("Totally {} tugua downloaded.".format(count))
		#tugua_download("http://www.dapenti.com/blog/more.asp?name=xilei&id=86617", date="20140130")
	except:
		logger.critical("!!! Exception occurred !!!", exc_info=True)
	logger.info("--------------------------------")
	