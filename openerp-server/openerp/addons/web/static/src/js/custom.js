/***** Start Ticket 3050 */
var storage = window.localStorage;

function menu(a) {
	
	if(storage.getItem('side') == 'hide'){
		storage.setItem('side','block');
	}else{
		storage.setItem('side','hide');
	}
	
	
	if(storage.getItem('side') == 'hide'){
		$('td.oe_leftbar').removeClass('block').addClass('hide sidebarhidden')
	}
	if(storage.getItem('side') == 'block'){
		$('td.oe_leftbar').removeClass('hide').addClass('block sidebarshown')
	}
	
    $(window).trigger('resize.stickyTableHeaders');
    if ($(".oe_leftbar").is(':visible'))
        $(".oe_leftbar").addClass('sidebarshown').removeClass('sidebarhidden');
}
/***** End Ticket 3050 */

/***** Start Ticket 3115 */
function mainmenu(a) {
    $('.oe_secondary_menu_section').not($(a)).css('color', '#c0c6ce !important;');
    $(a).css('color', '#FFF !important;');
    $('.oe_secondary_menu_section').not($(a)).css('border-bottom', '1px solid rgba(192, 198, 206, 0.4)');
    $(a).css('border-bottom', '0px solid');
    $(a).next().toggle();
    $('.oe_secondary_submenu').not($(a).next()).hide();
}
/***** End Ticket 3115 */

/** Sidemenu Loading
 **************************************************************** **/
function submenu(a) {
    //ajaxindicatorstart();
	setTimeout(function () {
        ajaxindicatorstop();
		url_function();
    }, 500);
}
/** End Sidemenu Loading
 **************************************************************** **/


/** Ajax Loading
 **************************************************************** **/
function ajaxindicatorstart(text) {
    if (jQuery('body').find('#resultLoading').attr('id') != 'resultLoading') {
        var x = document.getElementsByTagName("body")[0];
        $(x).waitMe({
            effect: 'stretch',//win8_linear
            text: 'Please wait...',
            bg: 'rgba(255, 255, 255,0.7)',
            color: '#000'
        });
    }
}

function ajaxindicatorstop() {
    $('body').waitMe('hide');
}

var interval = '';
$(document).ready(function () {
    //ajaxindicatorstart();
    interval = setInterval(explode, 2000);
});

function explode() {
    if (jQuery.active == 0) {
        ajaxindicatorstop();
        clearInterval(interval);
    } else {
        //ajaxindicatorstart();
    }

}
/** End Ajax Loading
 **************************************************************** **/
 
/***** Start Ticket 3116 */
/** Toast
 **************************************************************** **/
toastr.options = {
    "closeButton": true,
    "debug": false,
    "newestOnTop": true,
    "progressBar": true,
    "positionClass": "toast-top-right",
    "preventDuplicates": true,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000", // How long the toast will display without user interaction
    "extendedTimeOut": "1000", // How long the toast will display after a user hovers over it
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "slideDown",
    "hideMethod": "slideUp"
};
/** End Toast
 **************************************************************** **/
/***** End Ticket 3116 */

/***** Start Ticket 3121 */
/** Sidebar Scrolling
 **************************************************************** **/
$(window).on('scroll', function () {
    if ($(this).scrollTop() > 50) {
        $('.totopbutton').removeClass('animated bounceOutDown').addClass('animated bounceInUp').show();
        $('.oe_secondary_menus_container').css({'margin-top': '-75px', 'position': 'fixed', 'width': '220px'});
    } else {
        $('.totopbutton').removeClass('animated bounceInUp').addClass('animated bounceOutDown');
        $('.oe_secondary_menus_container').css({'margin-top': '0px', 'position': 'inherit', 'width': 'inherit'});
    }
});
/** End Sidebar Scrolling
 **************************************************************** **/
/***** End Ticket 3121 */
 
/***** Start Ticket 3120 */
/****  Full Screen Toggle  ****/
var doc = document;
var docEl = document.documentElement;
function toggleFullScreen() {
    if (!doc.fullscreenElement && !doc.msFullscreenElement && !doc.webkitIsFullScreen && !doc.mozFullScreenElement) {
        if (docEl.requestFullscreen) {
            docEl.requestFullscreen();
        } else if (docEl.webkitRequestFullScreen) {
            docEl.webkitRequestFullscreen();
        } else if (docEl.webkitRequestFullScreen) {
            docEl.webkitRequestFullScreen();
        } else if (docEl.msRequestFullscreen) {
            docEl.msRequestFullscreen();
        } else if (docEl.mozRequestFullScreen) {
            docEl.mozRequestFullScreen();
        }
    } else {
        if (doc.exitFullscreen) {
            doc.exitFullscreen();
        } else if (doc.webkitExitFullscreen) {
            doc.webkitExitFullscreen();
        } else if (doc.webkitCancelFullScreen) {
            doc.webkitCancelFullScreen();
        } else if (doc.msExitFullscreen) {
            doc.msExitFullscreen();
        } else if (doc.mozCancelFullScreen) {
            doc.mozCancelFullScreen();
        }
    }
}
/***** End Ticket 3120 */

/***** Start Ticket 3121 */
function totop(e) {
    if ($(this).scrollTop() > 10) {
        $('html,body').animate({scrollTop: 0}, "fast");
        return false;
    }
}
/***** End Ticket 3121 */

/***** Start Ticket 3110 */
$.extend($.ui.dialog.prototype.options, {
    modal: true,
    resizable: false,
    draggable: false,
	open: function (event, ui) {
		/***** For Popup Validation */
		setTimeout(function(){
		   field_modal_validation();
		}, 500);
		/***** For Popup Validation */
		$('body').css('overflow','hidden');
    }
});
/***** End Ticket 3110 */

/***** Start Ticket 2984 */
function url_function(){
	if(window.location.href.indexOf("action=733") > -1) {
	   $('body').find('.oe_view_manager_switch').hide()
	   $('body').css('overflow-x','hidden');
	   $('table.oe_tree_table.oe-treeview-table').stickyTableHeaders({marginTop:32});
	}
}
setTimeout(function(){
   url_function();
   footer();
}, 500);
/***** End Ticket 2984 */

function greetings(display_name) {
	console.log(display_name)
	var myDate = new Date();
	/* hour is before noon */
	if (myDate.getHours() < 12) {
		return "","Good Morning " + display_name + "! " + "Have a wonderful day";
	}
	else  /* Hour is from noon to 5pm (actually to 5:59 pm) */
	if (myDate.getHours() >= 12 && myDate.getHours() <= 17) {
		return "","Good Afternoon " + display_name + "! "+"Have a wonderful day";
	}
	else  /* the hour is after 5pm, so it is between 6pm and midnight */
	if (myDate.getHours() > 17 && myDate.getHours() <= 24) {
		return "","Good Evening " + display_name + "! "+ "Have a wonderful day";
	}
	else {
		return "I'm not sure what time it is!", null;
	}
}

function callback_login(login){
	toastr.success(greetings(login), "Welcome! "+login);
	footer();
	/* $('.remove_this_css').remove;
	$('.slimScrollDiv').css('height','auto');
	$('.oe_secondary_menus_container').css('height','auto'); */
}

/***** Ticket 3237 */
/* Except Special Character */
var specialKeys = new Array();
	specialKeys.push(8); //Backspace
	specialKeys.push(9); //Tab
	specialKeys.push(46); //Delete
	specialKeys.push(36); //Home
	specialKeys.push(35); //End
	specialKeys.push(37); //Left
	specialKeys.push(39); //Right			

function aplhanumonly(e) {	
	var keyCode = e.keyCode == 0 ? e.charCode : e.keyCode;
	var ret = ((keyCode >= 48 && keyCode <= 57) || (keyCode >= 65 && keyCode <= 90) || (keyCode >= 97 && keyCode <= 122) || (specialKeys.indexOf(e.keyCode) != -1 && e.charCode != e.keyCode));
	return ret;
}
/* End Except Special Character */

/* For Email validation */
function email_validation(e) {	
	var keyCode = e.keyCode == 0 ? e.charCode : e.keyCode;
	var ret = ((keyCode >= 48 && keyCode <= 57) || (keyCode >= 65 && keyCode <= 90) || (keyCode >= 97 && keyCode <= 122) || (specialKeys.indexOf(e.keyCode) != -1 && e.charCode != e.keyCode));
	if(keyCode == 46 || keyCode == 64){ //allowed keyCode . ( ) -
		return true;
	}
	return ret;
}

function validateEmail(email) {	
	var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
	return re.test(email);
}

function email_validationn(e,ele) {
	$('body').find('.oe_form_button_save').attr('disabled',true);
	$(ele).text("");
	var email = $(ele).val();
	if (validateEmail(email)) {
	  $('body').find('.oe_form_button_save').attr('disabled',false);
	} else {
	  //toastr.error('Invalid Email ID.', 'Error');
	  swal("Oops Error", 'Invalid Email ID.', "error");
	}
	return false;
}
/* End For Email validation */

/* For Float Values */
function aplhanum_expect(e) {	
	var keyCode = e.keyCode == 0 ? e.charCode : e.keyCode;
	var ret = ((keyCode >= 48 && keyCode <= 57) || (keyCode >= 65 && keyCode <= 90) || (keyCode >= 97 && keyCode <= 122) || (specialKeys.indexOf(e.keyCode) != -1 && e.charCode != e.keyCode));
	if(keyCode == 46 || keyCode == 40 || keyCode == 41 || keyCode == 45 || keyCode == 32){ //allowed keyCode . ( ) - space
		return true;
	}
	return ret;
}
/* End For Float Values */

/* Only Numbers */
function numberonly(evt) {
    evt = (evt) ? evt : window.event;
    var charCode = (evt.which) ? evt.which : evt.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
        return false;
    }
    return true;
}
/* End Only Numbers */

/* Only Letters */
function lettersOnly(evt) {
	evt = (evt) ? evt : window.event;
    var charCode = (evt.which) ? evt.which : evt.keyCode;
    if ((charCode > 64 && charCode < 91) || (charCode > 96 && charCode < 123) || charCode == 8 || charCode == 32) {
        return true;
    }
    return false;
}
/* End Only Letters */
/***** End Ticket 3237 */

/***** Current year in copyright */
var d = new Date();
var n = d.getFullYear();
function footer(){
	setTimeout(function(){
		$('#curntyear').text(n);
		$('#nextyear').text(n+1);
	}, 500);
}
/***** End Current year in copyright */

function url(action){	
	var toAra = action.split(",");
	var opt = false;	
	if(window.location.href.indexOf("view_type=form") > -1){
		$.each(toAra,function(key,val){
			if((window.location.href.indexOf("action="+val) > -1)) {
			 opt = true;
			 return;
			}
		});	
	}
	return opt;
}


/***** Start Ticket 3315 */
function field_validation(){
	/***** fettling_qty Validation */
	if(url('684') == true){
		$('body').find('.inward_accept_qty input').on('keyup',function(){
			//e = $('body').find('.fettling_qty input').val();
			e = $('body').find('.fettling_qty span').text();
			var r = $(this).val();
			if(parseInt(e) < parseInt(r)){
				$('body').find('.oe_form_button_save').attr('disabled',true);
				$('body').find('.inward_reject_qty input').val('');
				swal("Error", 'Accepted qty should be less than '+e, "error");			
				$('body').find('.inward_accept_qty input').addClass('has_error').select();
			}else if(parseInt(e) >= parseInt(r)) {
				var res = e - r;
				$('body').find('.inward_reject_qty input').val(res);
				$('body').find('.oe_form_button_save').attr('disabled',false);
				$('body').find('.inward_accept_qty input').removeClass('has_error');
			}else{			
				$('body').find('.oe_form_button_save').attr('disabled',false);
				$('body').find('.inward_accept_qty input').removeClass('has_error');
			}
		});
	}
	/***** fettling_qty Validation */	
}
/***** End Ticket 3315 */

/***** For Popup Validation */
function field_modal_validation(){
	
}
/***** For Popup Validation */