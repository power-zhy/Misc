var show_str = "显示目录";
var hide_str = "隐藏目录";
var prev_str = "上一页";
var next_str = "下一页";

String.prototype.trim=function(){
	return this.replace(/(^\s*)|(\s*$)/g, "");
};

Date.prototype.Format = function (fmt) { //author: meizz 
	var o = {
		"M+": this.getMonth() + 1,
		"d+": this.getDate(),
		"h+": this.getHours(),
		"m+": this.getMinutes(),
		"s+": this.getSeconds(),
		"q+": Math.floor((this.getMonth() + 3) / 3),
		"S": this.getMilliseconds()
	};
	if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
	for (var k in o)
	if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
	return fmt;
}

function insertCatalogue() {
	var html = "<ul id='catalogue'>";
	var count = 0;
	$(".section").each(function(index, element) {
		var id = $(element).attr("id");
		var text = $(element).children(".subtitle").text().trim();
		html += "<li><a href=#" + id + ">" + text + "</a></li>";
		count ++;
	});
	html += "</ul>";
	if (count)
		$("#title").after("<div><a id='show_hide'></a>" + html + "</div>");
};

function showCatalogue() {
	$("#show_hide").html(hide_str);
	$("#catalogue").show();
	$("#show_hide").attr("href", "javascript:hideCatalogue()");
};

function hideCatalogue() {
	$("#show_hide").html(show_str);
	$("#catalogue").hide();
	$("#show_hide").attr("href", "javascript:showCatalogue()");
};

function insertEmbedFrame() {
	$("embed").each(function(index, element) {
		var width = $(element).attr("width");
		var height = $(element).attr("height");
		var src = $(element).attr("src");
		/*frame = document.createElement("iframe");
		if (width)
			$(frame).attr("width", width);
		if (height)
			$(frame).attr("height", height);
		$(frame).attr("src", src);
		$(frame).attr("allowfullscreen", "");
		$(frame).attr("frameborder", "0");
		$(element).after(frame);*/
		var html = "<iframe src='" + src + "' ";
		if (width != undefined)
			html += "width='" + width + "' ";
		if (height != undefined)
			html += "height='" + height + "' ";
		html += "allowfullscreen='' />";
		$(element).after(html);
		$(element).detach();
	});
};

function insertQuickNav() {
	var addDate = function(dateStr, daysDelta) {
		var date = new Date(dateStr.substr(0, 4) + "." + dateStr.substr(4, 2) + "." + dateStr.substr(6, 2));
		var tmp = date.valueOf() + daysDelta * 24 * 60 * 60 * 1000;
		date = new Date(tmp);
		return date.Format("yyyyMMdd");
	};
	var path = window.location.pathname;
	if (path[path.length-1] == '/')
		path = path.substr(0, path.length-1);
	path = path.substr(path.length-8, 8);
	var pathPrev = addDate(path, -1);
	var pathNext = addDate(path, 1);
	var $html = $("<div>").addClass("quick_nav");
	$html.append($("<a>").attr("href", "../" + pathPrev).text(prev_str));
	$html.append($("<a>").attr("href", "../" + pathNext).text(next_str));
	$("body").prepend($html.clone());
	$("body").append($html);
};

$(document).ready(function() {
	insertCatalogue();
	showCatalogue();
	insertEmbedFrame();
	insertQuickNav();
	
	// return to top function
	$(document.body).append("<a href=\"#0\" class=\"cd-top\">Top</a>");
	var offset = 300,
		//browser window scroll (in pixels) after which the "back to top" link opacity is reduced
		offset_opacity = 1200,
		//duration of the top scrolling animation (in ms)
		scroll_top_duration = 700,
		//grab the "back to top" link
		$back_to_top = $('.cd-top');
	//hide or show the "back to top" link
	$(window).scroll(function(){
		( $(this).scrollTop() > offset ) ? $back_to_top.addClass('cd-is-visible') : $back_to_top.removeClass('cd-is-visible cd-fade-out');
		if( $(this).scrollTop() > offset_opacity ) { 
			$back_to_top.addClass('cd-fade-out');
		}
	});
	//smooth scroll to top
	$back_to_top.on('click', function(event){
		event.preventDefault();
		$('body,html').animate({
			scrollTop: 0 ,
		 	}, scroll_top_duration
		);
	});
});
