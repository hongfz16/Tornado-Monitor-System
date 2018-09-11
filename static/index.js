$(document).ready(function(){
	if ("WebSocket" in window) {
		var ws_warning_path = 'ws://' + window.location.host + '/warning_websocket';
		var ws_warning = new WebSocket(ws_warning_path);
		ws_warning.onopen = function() {
			// ws_warning.send(1);
            // console.log("First sending request!")
		};
		ws_warning.onmessage = function(msg) {
			all_data = $.parseJSON(msg.data)
			data = all_data["str"]
			url = all_data["url"]
			for(var i=0; i<data.length; ++i) {
				warningdiv = $("#wswarning_"+url)
				warningdiv.prepend("<p class=\"list-group-item\">"+data[i]+"</p>");
				videoheight = $("#video_panel_"+url).height()
				warningheight = $("#warning_panel_"+url).height()
				if(videoheight<warningheight) {
					warningdiv.children().last().remove()
				}
			}
			// ws_warning.send(1);
            // console.log("Sending request!")
		};
		ws_warning.onerror = function(e) {
			console.log(e);
			// ws_warning.send(-1);
		};
	} else {
		alert("WebSocket not supported");
	}
});
window.onbeforeunload = function() {
    // ws_warning.send(-2)
    ws_warning.onclose = function () {
        console.log('Closing...');
    }; // disable onclose handler first
    ws_warning.close()
};