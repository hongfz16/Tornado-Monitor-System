$(document).ready(function(){
	if ("WebSocket" in window) {
		var ws_warning_path = 'ws://' + window.location.host + '/warning_websocket';
		var ws_warning = new WebSocket(ws_warning_path);
		ws_warning.onopen = function() {
			ws_warning.send(1);
            console.log("First sending request!")
		};
		ws_warning.onmessage = function(msg) {
			data = $.parseJSON(msg.data)
			data = data["str"]
			for(var i=0; i<data.length; ++i)
				$("#wswarning").append(data[i]+"<br>");
			ws_warning.send(1);
            console.log("Sending request!")
		};
		ws_warning.onerror = function(e) {
			console.log(e);
			ws_warning.send(-1);
		};
	} else {
		alert("WebSocket not supported");
	}
});
window.onbeforeunload = function() {
    ws_warning.send(-2)
    ws_warning.onclose = function () {
        console.log('Closing...');
    }; // disable onclose handler first
    ws_warning.close()
};