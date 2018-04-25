'use strict';

class Bot{
	constructor(){	
		this.oauth = {
	        "client_id" : "189476471381.188816274721",
	        "client_secret" : "0907369e1a6c003f9efc260e0d3b3149",
	        "scope" : "bot incoming-webhook channels:history channels:read channels:write chat:write:bot links:write team:read groups:write groups:read groups:history",
    	};
    	this.verification = "2kFxOSOhtAjqhCMsQbIsfv9o";
	}
}

var exports = module.exports = {};

exports.Bot = Bot;