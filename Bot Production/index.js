'use strict';
const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const http = require('http')
const fs = require('fs');
const request = require('request');
const botserver = require('./app');
const apiToken = require('./install-server-prodcution/apiToken');
var mysql = require('mysql');
var pool;
var Bot = require("./install-server-prodcution/bot")
var lastTs = 0;


// connect to db
function connectDB() 
{
	pool = mysql.createPool({
	  host     : 'localhost',
	  user     : 'root',
	  password : '1234',
	  database : 'slackfaqproduction',
	    connectionLimit : 5,               // this is the max number of connections before your pool starts waiting for a release
	    multipleStatements : true           // I like this because it helps prevent nested sql statements, it can be buggy though, so be careful
	});


	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}

	  	console.log('Connection established');
	  	connection.release();
	});
};




var router = express.Router();

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// start app and connect to db
const server = app.listen(8000, () => {  
console.log('Express server listening on port %d in %s mode', server.address().port, app.settings.env);});
connectDB();


app.get('/support', function(req, res){
	//makesure external /thanks call doesnt crash the app
	console.log("Over here in /support");
	fs.readFile('./install-server-prodcution/support.html', function (err, html) 
		{
			if (err) 
			{
				console.log("File reading error in renderHTML");
				res.writeHead(404);
				res.write("File not Found!");
			    throw err; 
			}       
			else
			{
			   	res.writeHeader(200, {"Content-Type": "text/html"});  
			    res.write(html);  	
			}

			res.end();  
    	});
  
});


app.get('/privacy', function(req, res){
	//makesure external /thanks call doesnt crash the app
	console.log("Over here in /support");
	fs.readFile('./install-server-prodcution/privacy.html', function (err, html) 
		{
			if (err) 
			{
				console.log("File reading error in renderHTML");
				res.writeHead(404);
				res.write("File not Found!");
			    throw err; 
			}       
			else
			{
			   	res.writeHeader(200, {"Content-Type": "text/html"});  
			    res.write(html);  	
			}

			res.end();  
    	});
  
});





var bot = new Bot.Bot();


app.get('/thanks', function(req, res){
	//makesure external /thanks call doesnt crash the app
	console.log("Over here in /thanks");
  var data = {form: {
      client_id: bot.oauth.client_id,
      client_secret: bot.oauth.client_secret,
      code: req.query.code
  }};
  request.post('https://slack.com/api/oauth.access', data, function (error, response, body) {
    if (!error && response.statusCode == 200) 
    {
		// You are done.
		// If you want to get team info, you need to get the token here
		let token = JSON.parse(body); // Auth token

		//if exist, delete then enter team tokens, else just enter it in db
		delete_team_if_exist(token, function(){
			insert_tokens_in_db(token);
		});
		
		var textInFile = token.team_name+"\n"+token.access_token+"\n"+token.bot.bot_access_token+"\n";
		console.log("In thanks, token",token);
		fs.writeFile("./install-server-prodcution/token.txt", textInFile, function(err) 
		{
		    if(err)
		        return console.log(err);
		  
		    console.log("The file was saved!");
		}); 

		console.log(textInFile);
		fs.readFile('./install-server-prodcution/thanks.html', function (err, html) 
		{
			if (err) 
			{
				console.log("File reading error in renderHTML");
				res.writeHead(404);
				res.write("File not Found!");
			    throw err; 
			}       
			else
			{
			   	res.writeHeader(200, {"Content-Type": "text/html"});  
			    res.write(html);  	
			}

			res.end();  
    	});
    }


  });

});



app.get('/botMention/:teamID/:channelID/:ts',botserver);
app.get('/channel_join/:teamID/:channelID',botserver);



app.get('/install', function(req, res){
	fs.readFile('./install-server-prodcution/install.html', function (err, html) 
	{
		if (err) 
		{
			console.log("File reading error in renderHTML");
			res.writeHead(404);
			res.write("File not Found!");
		    throw err; 
		}       
		else
		{
		   	res.writeHeader(200, {"Content-Type": "text/html"});  
		    res.write(html);  	
		}

    	res.end();  
    });
    
});


app.post('/listening', function(req, res)
{	

	if(req.body.challenge == undefined)
	{
        if (req.body.token == undefined)
        {
            console.log("Error encountered");
            res.end();
        }

        // catch repeated events
        if(parseFloat(req.body.event.ts) <= lastTs && lastTs != 0)
        {
			console.log("repeated req", lastTs, parseFloat(req.body.event.ts));
        }
        // new valid message, update time
        else
        {
        	// new valid message, update time
        	lastTs = req.body.event.ts;
        
	        // if our bot joins a channel
	        if(req.body.event.type == "message" && (req.body.event.subtype == "channel_join" || req.body.event.subtype == "group_join"))
	        {
	        	// if comes here, do db call to get our bot id and then match it with theirs
	        	var reqBotId = req.body.event.user;
	        	var teamID = req.body.team_id;
	        	var channelID = "";
	        	// if channel joined was our bot, call load history in app.js
	        	is_our_bot(reqBotId,teamID,function(isTrue){
	        		if(isTrue)
	        		{
	        			channelID = req.body.event.channel;
	        			console.log("Our bot joined channel:", channelID);
	        			res.redirect("/channel_join"+"/"+teamID+"/"+channelID);
	        		}
	        		else
	        			console.log("Not our bot.");	
	        	});
	        }
	        // if message and not a bot
	        else if(req.body.event.type == "message" && (req.body.event.bot_id == undefined || req.body.event.subtype != "bot_message"))
	        {
	        	// WARNING! this case is still triggered when our bot sends a message //
	        	
	    		var message = req.body.event.text;
	    		var botMention = message.split(" ")[0];

	    		// our bot maybe mentioned
	    		if(botMention[0] == "<" && botMention[1] == "@")
	    		{
	    			get_botID(req.body.team_id, function(botID)
	    			{
	    				var mentionedID = message.substring(message.indexOf("@")+1,message.indexOf(">"));
	    				if(botID == mentionedID)
	    				{
	    					console.log("Our bot was called");
	    					insert_event_in_db(req.body,true);
	    					res.redirect("/botMention"+"/"+req.body.team_id+"/"+req.body.event.channel+"/"+req.body.event.ts);
	    				}
	    				else
	    					console.log("else 1 under our bot was called",req.body);

	    			});
	    		}
	    		else
	    			console.log("else 2 under our bot was called", req.body);
	        }
	    }
	}
	// only used for validating slack challenge
	else
	{	
		reply_to_challenge(req,res);
	}
});




function get_botID(teamID,callback)
{
	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established
		connection.query('select botID from teamTokens where teamID = "'+teamID+'";', 
		function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	callback(rows[0].botID);
		    }
		    connection.release();
	  	});	

	});
}

function reply_to_challenge(req,res)
{
	console.log("challenge:",req.body.challenge);
	res.status(200).send({ challenge: req.body.challenge});
	res.setHeader('content-type', 'application/json');
	res.end();	
}


// insert neccessary stuff into db
function insert_tokens_in_db(json)
{
	var teamID = json.team_id;
	var teamName = json.team_name;
	var userToken  = json.access_token;
	var botToken =  json.bot.bot_access_token;
	var botID = json.bot.bot_user_id;

	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established

		connection.query('insert into teamTokens values("'+teamID+'","'+teamName+'","'+userToken+'","'+botToken+'","'+botID+'")', 
			function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	console.log("New Team Added: ",teamID,teamName);
		    }
		    connection.release();
	  	});
	});
}


function delete_team_if_exist(json, callback)
{
	var teamID = json.team_id;

	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established

		connection.query('delete from teamTokens where teamID = "'+teamID+'"', 
			function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	callback();
		    }
		    connection.release();
	  	});
	});
}



function insert_event_in_db(body,isBotMention)
{	
	var ts = body.event.ts;
	var channelID = body.event.channel;
	var text = body.event.text;

	// if bot was mention, then remove bot token from text
	if(isBotMention)
	{
		text = text.substring(text.indexOf(">")+2, text.length);
		console.log("Excluded bot msg is:",text);
	}

	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established
		connection.query('insert into events values("'+ts+'","'+channelID+'","'+ mysql_real_escape_string(text)+'")', 
		function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	console.log("added row: ",channelID,ts,"->",text);
		    }
		    connection.release();
	  	});	

	});

}


function mysql_real_escape_string (str) {
    return str.replace(/[\0\x08\x09\x1a\n\r"'\\\%]/g, function (char) {
        switch (char) {
            case "\0":
                return "\\0";
            case "\x08":
                return "\\b";
            case "\x09":
                return "\\t";
            case "\x1a":
                return "\\z";
            case "\n":
                return "\\n";
            case "\r":
                return "\\r";
            case "\"":
            case "'":
            case "\\":
            case "%":
                return "\\"+char; // prepends a backslash to backslash, percent,
                                  // and double/single quotes
        }
    });
}


function is_our_bot(reqBotId, teamID, callback)
{

	var isTrue = 0;
	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established
		connection.query('select botID from teamTokens where teamID = "'+teamID+'";', 
		function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
				callback(0);
			}
		  	else
		    {
		    	if(reqBotId == rows[0].botID)
		    		callback(1);
		    	else
		    		callback(0);
		    }
		    connection.release();
	  	});	

	});
}