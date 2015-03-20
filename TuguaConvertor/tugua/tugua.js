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

