
window.onbeforeunload = function (){
	if (window.event.clientY>0||window.event.altKey){
		window.onbeforeunload = null;
	}else{
		// alert("quit");
		$.ajax({
			type:"post";
			url:"main?action=logout";
			data:"";
			success:function (data) {
			}
		});
	}
}