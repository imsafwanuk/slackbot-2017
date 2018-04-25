'use strict';
const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const http = require('http')
const fs = require('fs');
const request = require('request');
const botserver = require('../app');
const apiToken = require('./apiToken');
var mysql = require('mysql');
var pool;
var Bot = require("./bot")
var lastTs = 0;


// connect to db
function connectDB() 
{
	pool = mysql.createPool({
	  host     : 'localhost',
	  user     : 'root',
	  password : '1234',
	  database : 'simple',
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




var bot = new Bot.Bot();


app.get('/thanks', function(req, res){
	
	console.log("Over here:");
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
		insert_tokens_in_db(token);
		var textInFile = token.access_token+"\n"+token.bot.bot_access_token+"\n";
		fs.writeFile("./token.txt", textInFile, function(err) 
		{
		    if(err)
		        return console.log(err);
		  
		    console.log("The file was saved!");
		}); 

		console.log(textInFile);
		fs.readFile('./thanks.html', function (err, html) 
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


// app.get('/try',function(req,res){
// 	console.log("Try:",req.url);
// 	// request.get('http://localhost:8000/bot/a/b');
// 	res.redirect('/bot'+"/1496153093.362388"+"/C5JM0L2M6");
// });

app.get('/message/:ts/:channelID',botserver);

app.get('/channel_join/:channelID/:botID',botserver);



app.get('/install', function(req, res){
	fs.readFile('./install.html', function (err, html) 
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
         	// console.log("new message", lastTs parseFloat(req.body.event.ts));
        
	        // if our bot joins a channel
	        if(req.body.event.type == "message" && req.body.event.subtype == "channel_join")
	        {
	        	// console.log("\n\nIn channel_join\n\n");
	        	// if comes here, do db call to get our bot id and then match it with theirs
	        	var reqBotId = req.body.event.user;
	        	var teamID = req.body.team_id;
	        	
	        	// if channel joined was our bot, call load history in app.js
	        	is_our_bot(reqBotId,teamID,function(isTrue){
	        		if(isTrue)
	        		{
	        			var channelID = req.body.event.channel;
	        			console.log("Our bot joined channel:", channelID);
	        			res.redirect("/channel_join"+"/"+req.body.event.channel+"/"+req.body.event.user);
	        		}
	        		else
	        			console.log("Not our bot.");	
	        	});
	        }
	        // if bot removed from a channel
	        else if(req.body.event.type == "message" && req.body.event.subtype == "channel_leave")
	        {
	        	// console.log("\n\nIn channel_leave\n\n");
	        	
	        	// if comes here, do db call to get our bot id and then match it with theirs
	        	var reqBotId = req.body.event.user;
	        	var teamID = req.body.team_id;
	        	
	        	// if channel joined was our bot, call load history in app.js
	        	is_our_bot(reqBotId,teamID,function(isTrue){
	        		if(isTrue)
	        		{
	        			var channelID = req.body.event.channel;
	        			console.log("Our bot left channel:", channelID);
	        		}
	        		else
	        			console.log("Not our bot.");	
	        	});
	        }
	        // if message and not a bot
	        else if(req.body.event.type == "message" && (req.body.event.bot_id == undefined || req.body.event.subtype != "bot_message"))
	        {
	    		console.log("\n\nA real user sent a message\n\n");
	            insert_event_in_db(req.body);
	            res.redirect("/message"+"/"+req.body.event.channel+"/"+req.body.event.ts);
	        }
	    }
	}
	// only used for validating slack challenge
	else
	{	
		reply_to_challenge(req,res);
	}
});


function reply_to_challenge(req,res)
{
	console.log(req.body.challenge);
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
		    	console.log("added row: ",teamID,teamName);
		    }
		    connection.release();
	  	});
	});
}




function insert_event_in_db(body)
{	
	var ts = body.event.ts;
	var channelID = body.event.channel;
	var text = body.event.text;
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