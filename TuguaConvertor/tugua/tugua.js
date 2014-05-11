show_str = "显示目录"
hide_str = "隐藏目录"

String.prototype.trim=function(){
	return this.replace(/(^\s*)|(\s*$)/g, "");
}

function insertCatalogue() {
	html = "<ul id='catalogue'>";
	count = 0;
	$(".section").each(function(index, element) {
		id = $(element).attr("id");
		text = $(element).children(".subtitle").text().trim();
		html += "<li><a href=#" + id + ">" + text + "</a></li>";
		count ++;
	});
	html += "</ul>";
	if (count)
		$("#title").after("<div><a id='show_hide'></a>" + html + "</div>");
}

function showCatalogue() {
	$("#show_hide").html(hide_str);
	$("#catalogue").show();
	$("#show_hide").attr("href", "javascript:hideCatalogue()");
}

function hideCatalogue() {
	$("#show_hide").html(show_str);
	$("#catalogue").hide();
	$("#show_hide").attr("href", "javascript:showCatalogue()");
}

function insertEmbedFrame() {
	$("embed").each(function(index, element) {
		width = $(element).attr("width");
		height = $(element).attr("height");
		src = $(element).attr("src");
		/*frame = document.createElement("iframe");
		if (width)
			$(frame).attr("width", width);
		if (height)
			$(frame).attr("height", height);
		$(frame).attr("src", src);
		$(frame).attr("allowfullscreen", "");
		$(frame).attr("frameborder", "0");
		$(element).after(frame);*/
		html = "<iframe src='" + src + "' ";
		if (width != undefined)
			html += "width='" + width + "' "
		if (height != undefined)
			html += "height='" + height + "' "
		html += "allowfullscreen='' />"
		$(element).after(html)
		$(element).detach()
	});
}

$(document).ready(function() {
	insertCatalogue();
	showCatalogue();
	insertEmbedFrame();
});

