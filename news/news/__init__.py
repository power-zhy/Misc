# -*- coding: utf-8 -*-

import sys
if sys.version_info.major <= 2:
	reload(sys)
	sys.setdefaultencoding("UTF8")

import logging
import settings
handler = logging.StreamHandler()
formatter = logging.Formatter(
	fmt = getattr(settings, "LOG_FORMAT", None),
	datefmt = getattr(settings, "LOG_DATEFORMAT", None),
)
handler.setFormatter(formatter)
handler.setLevel(getattr(settings, "LOG_LEVEL", None))
logging.root.addHandler(handler)
