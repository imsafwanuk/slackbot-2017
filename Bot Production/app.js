'use strict';

var util = require('util');
var path = require('path');
var fs = require('fs');
var request = require('request')
var mysql = require('mysql');
var Bot = require('slackbots');
var connection;
var pool;

/*	requires for routing	*/
const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const http = require('http')
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));



/**	FOR MANUAL TESTING ONLY which allows extraction of messages from other teams channels/grps 
 *	and directly testing a query using getSimilarityTs.py
 */
  
var manualTestingFlag = 0;
var manualTestingToken = "";
var manualTestingChannel = [];
var botToken = "";	
var userToken = ""; 





// connect to db
function connectDB(teamID,callback) 
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
	  	connection.query('select teamName,userToken,botToken,botID from teamTokens where teamID = "'+teamID+'";', 
			function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	var bot_info_dic = {
		    		userToken :rows[0].userToken,
		    		botToken : rows[0].botToken,
		    		teamName : rows[0].teamName,
		    		botID : rows[0].botID,
		    	}

		    	callback(bot_info_dic);
		    }
		    connection.release();
	  	});

	});
};


function get_text(channelID,ts,callback)
{
	pool.getConnection(function(err,connection){
		if(err)
			return res.send(400);

		// connection established
		connection.query('select text from events where (channelID = "'+channelID+'") and (ts = "'+ts+'");', function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	console.log("In get_text",rows[0].text);
		    	callback(rows[0].text);
		    }
		    connection.release();
	 	});
	});
}


app.get('/botMention/:teamID/:channelID/:ts',function(req,res){

	connectDB(req.params.teamID,function(bot_info_dic) {
		bot_mention_event(req, res, bot_info_dic);
	});
	res.end();
});


function bot_mention_event(req,res, bot_info_dic)
{

	var faqbot = new FAQBot({
	    token: bot_info_dic.botToken,
	    name: "faqbot",
	    userToken: bot_info_dic.userToken,
	    botToken: bot_info_dic.botToken,
	    teamName: bot_info_dic.teamName,
	    botID: bot_info_dic.botID,
	});


	var channelID = req.params.channelID;
	var ts = req.params.ts;

	util.inherits(FAQBot, Bot);
	var self = faqbot._runUpdate(req.params.channelID);

	get_text(channelID,ts,function(text)
	{
		// remove the text from db
		remove_bot_mention_text(channelID, ts);

		console.log("In app message:",text);
		if(text == "update chat")
		{
			console.log("Asked to update chat");
			self._getChannelName(channelID,function(channelName){
				self._updateHistory(channelID,channelName);
			});

		}
		else
		{
			console.log("Asked a question");
			// send reply to appropiate channel
			self._getChannelName(channelID,function(channelName){
				self._getAnswer(channelID, channelName, text);
			});
			
		}
	});
}


function remove_bot_mention_text(channelID, ts)
{
	pool.getConnection(function(err,connection){
		if(err)
			console.log(err);

		// connection established
		connection.query('delete from events where (channelID = "'+channelID+'") and (ts = "'+ts+'");', function(err, rows, fields) 
		{
			if(err)
			{
				console.log(err);
			}
		  	else
		    {
		    	console.log("Row of text of ts:",ts,"deleted");
		    }
		    connection.release();
	 	});
	});
}


app.get('/channel_join/:teamID/:channelID',function(req,res){

	connectDB(req.params.teamID,function(bot_info_dic){
		bot_join_event(req, res, bot_info_dic);
	});
	res.end();
});


function bot_join_event(req,res,bot_info_dic)
{
	var faqbot = new FAQBot({
	    token: bot_info_dic.botToken,
	    name: "faqbot",
	    userToken: bot_info_dic.userToken,
	    botToken: bot_info_dic.botToken,
	    teamName: bot_info_dic.teamName,
	    botID: bot_info_dic.botID,
	});

	console.log("In join app.js:",req.params.channelID);
	util.inherits(FAQBot, Bot);
	faqbot._run(req.params.channelID);
}



module.exports = app;



// this function removes white space, if any, before a '?'
String.prototype.removeSpace=function() {
	var self = this;
	self = this.replace(/\s+/g,' ').trim();
	if(self[self.length-2] == ' ')
	{
		return self.substr(0, self.length-2) + self.substr(self.length-1, self.length);	
	}
    else
    	return self;
}

function convertToSlackTime(formattedTs)
{
	formattedTs = formattedTs.toString();
	var dotIndex = formattedTs.length-6;		// 6 is the number of digits after '.' in slack's ts
	var slackTs = formattedTs.slice(0,dotIndex)+"."+formattedTs.slice(dotIndex);
	return slackTs;
}

// watches for file additions
function watchFile(filepath, oncreate, ondelete)
{
	var filedir = path.dirname(filepath);
	var filename = path.basename(filepath);

	fs.watch(filedir,function(event,who)
	{
		if(event === 'rename' && who === filename)
		{
			if(fs.existsSync(filepath))
			{
				console.log("File created '"+filename+"'");
			}
			else
			{
				console.log("File deleted '"+filename+"'");
			}
		}
	});
}


/**
 * TS in slack stands for exact time of message. So using the ts time, we can directly link to a message.
 * ths function just places a p infront of the ts and removes the dot in the middle
*/
function formatTs(ts)
{

	var newTs = "p"+ts.replace(/\./g,'');
	return newTs;
}

// this function removes new lines, if any, before a '?'
String.prototype.removeNewLine=function() {
	var self = this;
	self = this.replace('\n',' ');
    	return self;
}

/**
 * Constructor function. It accepts a settings object which should contain the following keys:
 *      token : the API token of the bot (mandatory)
 *      name : the name of the bot (will default to "FAQBot")
 *      dbPath : the path to access the database (will default to "data/FAQBot.db")
 *
 * @param {object} settings
 * @constructor
 *
 * @author Luciano Mammino <lucianomammino@gmail.com>
 */
var FAQBot = function Constructor(settings) {
    this.settings = settings;
    this.settings.name = this.settings.name || 'FAQBot';
    this.botID = this.settings.botID || null;
    this.teamID = this.settings.teamID || null;
    this.teamName = this.settings.teamName || null;
    this.botToken = this.settings.botToken || null;
    this.userToken = this.settings.userToken || null;
    this.channelName = null;
};





/**
 * Run the bot
 * @public
 */
FAQBot.prototype._runUpdate = function (channelID) {
    FAQBot.super_.call(this, this.settings);
    return this;
};



FAQBot.prototype._run = function (channelID) {

    FAQBot.super_.call(this, this.settings);

    var self = this;
    this._getChannelName(channelID,function(channelName)
    {
    	self._syncChannel(channelID,channelName);
    });
};


// run script that processes and automates the retrieved messages from slack and finally create question-channelteam.txt
FAQBot.prototype._runBashSCript = function(fileName, channelID)
{
	var self = this;
	console.log("Starting bash script to automate question extraction process");
	var exec = require("child_process").exec,
		child;
	child = exec("./bash_automate.sh "+fileName, function(err,stdout,stderr)
	{
		var stdlines = stdout.split("\n");
		if(stdlines[stdlines.length-2] == "Done bashing")
		{
			self._giveAnswerText("Done loading questions.");
			var tableName = fileName.slice(0,-4);
			tableName = tableName.replace(/[^\w\s]/gi, '').toLowerCase()+"Table";
			self._get_last_question_id(tableName,fileName, channelID);
		}
		else
		{
			console.log("stderr: "+ stderr);	
			console.log("stderr: "+ stdout);
			self._giveAnswerText("No questions to load.");
		}
		
		if(err != null)
		{
			console.log("Error: "+ err);
		}
	});
}


FAQBot.prototype._giveAnswerLink = function (channelID, num, answer)
{
	var self = this;
	var colorCode = "";
	switch(num)
	{
		case 1:
			colorCode = "good";
			break;
		case 2:
			colorCode = "#073FC4";
				break;
		case 3:
			colorCode = "#07C4BD";
			break;
		case 4:
			colorCode = "warning";
			break;
		case 5:
			colorCode = "danger";
			break;
	}

	var params;
	num = "`"+num+"`";
	answer = "https://"+self.teamName+".slack.com/archives/"+channelID+"/"+answer;
	request.post({
		url: 'https://slack.com/api/chat.postMessage',
		formData: {
			token: self.botToken,
			channel: channelID,
			text: num,
			parse: 'full',
			attachments: '[{"text":"'+answer+'","color":"'+colorCode+'"}]',
			as_user:"true",
		},
	}, function(err,response){
		if(err)
			console.log(err);
		console.log("Give answer link response:",response);
	});
}



FAQBot.prototype._giveAnswerText = function (channelID, text)
{
	var self = this;
	self.postMessage(channelID, text, {as_user: true});
}



/**
 * Replyes to a message with a random Joke
 * @param {object} originalMessage
 * @private
 */
FAQBot.prototype._getAnswer = function (channelID, channelName, message)
{
	var self = this;
	var ts_list = [];
	var givenAnswers = 0;
	console.log("Starting bash script to get similar questions");
	var exec = require("child_process").exec,
		child;
	var arg = "'"+message + "' ";
	arg += channelName + " ";
	arg += channelName.replace(/[^\w\s]/gi, '').toLowerCase()+"Table";

	child = exec("./bash_get_question.sh "+ arg, function(err,stdout,stderr)
	{
		if(err)
			console.log(err);

		var lines = stdout.split("\n");
		if(lines[lines.length-2] == "Done bashing similar questions")
		{
			console.log("Done bashing similar questions");
			fs.readFile("similar-"+channelName+".txt","utf-8", function(err,data)
			{
				if(err)
				{
					return console.log(err);
				}

				lines = data.split("\n");
				if(lines[0][0] != "p")
				{
					self._giveAnswerText(channelID,"No matching questions found.");
					return;
				}
				for(var i=0;i<lines.length;i++)
				{
					if(lines[i][0] == "p")
					{
						givenAnswers++;
						self._giveAnswerLink(channelID, givenAnswers, lines[i]);
					}
				}
			});

		}
		if(err != null)
		{
			console.log("Error: "+ err);
		}
	});
};


FAQBot.prototype._getChannelName = function (channelID, callback) 
{
	var self = this;
	console.log("Getting channel name for Bot.");

	var urlInfo = "";

	if(channelID[0] == "C")
	{
		urlInfo = 'https://slack.com/api/channels.info';
	}
	else
	{
		urlInfo = 'https://slack.com/api/groups.info';
	}

	// get all channels the bot is in
	request.post({
		url: urlInfo,
		formData: {
			token: self.botToken,
			channel: channelID
		},
	}, function(err,response){
		var res = JSON.parse(response.body);
		if(channelID[0] == "C")
		{
			this.channelName = res.channel.name;
		}
		else
		{
			this.channelName = res.group.name;			
		}
		callback(this.channelName);
	});
}



function createTable(tableName)
{
	// create table
	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}

	  	connection.query("CREATE TABLE "+tableName+" (id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,question varchar(10000),ts varchar(50),PRIMARY KEY (id)) ENGINE=InnoDB  DEFAULT CHARSET=utf8;"
						, function(err, rows, fields) 
		{
			if(err)
			{
				console.log("Couldn't create Table: "+tableName);
			}
		  	else
		    {
		    	console.log("Table'"+tableName +"' succesfully created.");
		    }
	  	});		

	  	connection.release();
	});
	
}


// provide a channel or group name and it returns a table name. but doesnt check if the table exist already or not
function getTableName(name)
{
	return name.replace(/[^\w\s]/gi, '').toLowerCase()+"Table";
}



// sync channel only
FAQBot.prototype._syncChannel = function (channelID,channelName) {
	var self = this;

	console.log("DB syncing with channel...");
	console.log("channel name",channelName);
	
	var tableName = getTableName(channelName);
	
	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}
	  	connection.query('select 1 from '+tableName+' limit 1;', function(err, rows, fields) 
		{
			if(err || rows.length == 0)
			{
				// if channels/groups table doesnt exist
				if(err)
				{
					console.log("Table for this team '"+tableName+"' doesn't exist");
					console.log("Creating table with the name: "+tableName);
					createTable(tableName);
				}
				else if(rows.length == 0)
				{
					console.log("Table for this channel'"+channelName+"' exist but is empty.");
				}

				watchFile("/home/saf/Desktop/slack-faq/question-"+channelName+".txt",oncreate,ondelete);
				self._getHistory(channelID, channelName,0,"latest");	
			}
		  	else
		    {
		    	console.log("Connected to team:"+" table:"+tableName);
		    }

	  	});
	  
	  	connection.release();
	});
}

function oncreate()
{
	console.log("File created");
}

function ondelete()
{
	console.log("File deleted");
}




/**
 * to retreive history
 * Put this in between loadbot user and connect to db when bot starts to get last 1000 messages
 * It saves the messages in 2 formats, original and extracted and 
 * puts it in original-channelname and retreive-channelname respectively.
 */


// get the latest ts and getHistory
FAQBot.prototype._updateHistory = function(channelID, channelName) {
	
	var self = this;
	var tableName = channelName.replace(/[^\w\s]/gi, '').toLowerCase()+"Table";

	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}

	  	// get the latest ts
		connection.query('select ts from '+tableName+' order by ts desc limit 1;', function(err, rows, fields) 
		{
			if(err || rows.length == 0)
			{
				if(err)
				{
					console.log(err);
					console.log("Error in table '"+tableName+"' of this team ");
					self._giveAnswerText(channelID, "Opps something went wrong. Unable to update answer.\n Please wait while we reload the entire history. Won't be long.");
					createTable(getTableName(channelName));
				}
				//if it comes here then the table exist but is empty, so just get data from the start
				self._getHistory(channelID, channelName,0,"latest");	
			}
		  	else
		    {
		    	console.log("Got info from table: "+tableName);
		    	var ts = rows[0].ts;
		    	self._getHistory(channelID, channelName, ts, "oldest");
		    }
	  	});
	  	
	  	connection.release();
	});
	
};


FAQBot.prototype._getHistory = function (channelID, channelName, ts, latestOrOldest) {
	var self = this;
	var originalStream = "original-"+channelName+".txt";
	var retrieveStream = "retrieve-"+channelName+".txt";
	
	var urlHistory = "";

	if(channelID[0] == "C")
	{
		urlHistory = 'https://slack.com/api/channels.history';
	}
	else
	{
		urlHistory = 'https://slack.com/api/groups.history';
	}

	if(ts == 0)
	{
		fs.closeSync(fs.openSync(originalStream, 'w'));
		fs.closeSync(fs.openSync(retrieveStream, 'w'));
	}

	if(latestOrOldest == "latest")
	{
		request.post(
		{
			url: urlHistory,
			formData: 
			{
				token: self.userToken,
				channel: channelID,
				latest: ts,
				count: 1000,
			},
		}, function(err,response){
			self._deal_with_chat_history(err,response,latestOrOldest,channelID, channelName);
		});
	}
	else
	{
		ts = convertToSlackTime(ts);
		request.post(
		{
			url: urlHistory,
			formData: 
			{
				token: self.userToken,
				channel: channelID,
				oldest: ts,
			},
		}, function(err,response){
			self._deal_with_chat_history(err,response,latestOrOldest,channelID, channelName);
		});
	}
};

FAQBot.prototype._deal_with_chat_history = function(err,response, latestOrOldest, channelID, channelName)
{
	var self = this;
	var originalStream = "original-"+channelName+".txt";
	var retrieveStream = "retrieve-"+channelName+".txt";

	if(err)
	{
		cosole.log(err);
		console.log("Couldn't get history");
		return;
	}

	var res = JSON.parse(response.body);
	if(res.messages == undefined || res.messages.length == 0)
 	{
 		console.log("Channel empty..")
 		return;
 	}

	for(var i=0; i<res.messages.length; i++)
	{
		var ts = res.messages[i].ts;	//update time to oldest message extracted

		/* for original text	*/

		//if want to get rid of bot messge, subtype == "bot_message"
		if(channelID[0] == "C" || channelID[0] == "G" )
		{
			if (res.messages[i].type == "message" && (res.messages[i].subtype != "channel_join" || res.messages[i].subtype != "group_join") )
				fs.appendFileSync(originalStream, res.messages[i].text+"\n");
		}

		/* for retrieved text	*/

		//if want to get rid of bot messge, subtype == "bot_message"
		if(channelID[0] == "C" || channelID[0] == "G" )
		{
			//not a bot msg
			if(res.messages[i].bot_id == undefined)
			{
				var msg = "";
				msg+= res.messages[i].text;
				// dont get messages directed towards this bot
				if(msg.split(" ")[0] != "<@"+self.botID+">")
				{

					if (res.messages[i].type == "message" && (res.messages[i].subtype != "channel_join" || res.messages[i].subtype != "group_join") )
					{
						var text = res.messages[i].text.removeNewLine();
						var lastc = text.slice(-1);
						if( lastc == "." || lastc == "?" || lastc == "!" || lastc == ">" || lastc == ":" || lastc == " ")
						{
							fs.appendFileSync(retrieveStream, formatTs(ts)+"\t"+res.messages[i].text);
						}
						else	
						{
							fs.appendFileSync(retrieveStream, formatTs(ts)+"\t"+res.messages[i].text+".");
						}
					}
				}

			}
		}

	}

	// if has more then recursively call get history function
	if (res.has_more == true)
	{
		if(latestOrOldest == "oldest")
			ts = res.messages[0].ts;
		console.log("At time:",ts);
		console.log("Has more messages..");
		return self._getHistory(channelID,channelName,ts, latestOrOldest);
	}
	else
	{
		self._runBashSCript(channelName+".txt", channelID);
	}

}


function insert_in_db(question,ts,lastID,tableName,callback)
{
	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}
	 	connection.query('insert into '+tableName+' values("'+lastID +'",'+'"'+question+'"'+','+'"'+ts+'"'+')', function(err, rows, fields) 
		{
			if(err)
			{
				// if there is an error in retrieving query
				console.log("MySql Error dbLoadQuestions 2");
			}
		  	else
		    {
		    	console.log("added row: "+lastID);
		    	callback();
		    }
	  	});

	  	connection.release();
	});

	
}



// gets the ID of last question inserted in a given table
FAQBot.prototype._get_last_question_id = function(tableName,fileName, channelID)
{
	var self = this;
	var lastID = null;

	pool.getConnection(function(err, connection) {
		if(err){
	    	console.log('Error connecting to Db');
	    	return;
	  	}
		connection.query('select id from '+tableName+' order by id desc limit 1;', function(err, rows, fields) 
		{
			if(err)
			{
				// if there is an error in retrieving query
				console.log("MySql Error dbLoadQuestions 1\n", err);
			}
		  	else
		    {
		    	if(rows.length == 0)
		    		lastID = 0;
		    	else
		    		lastID = rows[0].id;	
		    	
	    		// get questions from file and save them in DB
	    		self._load_question_file(lastID,tableName, fileName, channelID)
		    }
	  	});	

	  	connection.release();
	});	
}



// laods questions and ts from file to main memory
FAQBot.prototype._load_question_file = function(lastID, tableName, fileName, channelID)
{
	var self = this;
	var list = [];
	fs.readFile("question-"+fileName,"utf-8", function(err,data)
	{

		if(err)
		{
			return console.log(err);
		}

		var lines = data.split("\n");
		if(lines.length == 0)
		{
			console.log("No questions to load.");
			return;
		}

		for(var i=0;i<lines.length;i++)
		{
			list.push(i);
		}

		var x = 0;

		var loopArray = function(list)
		{
			if(lines[x].length>0)
			{
				var parsedLine = lines[x].split("\t");
				var ts = parsedLine[0];
				var question = parsedLine[1];
				// call itself
				lastID++;
				insert_in_db(question,ts,lastID, tableName,function(){
					//set to next item 
					if(x == list.length-1)
					{
						console.log("Done loading questions.");
						self._giveAnswerText(channelID, "Chat history loaded!");
					}
					x++;
					if(x<list.length)
					{
						loopArray(list);
					}
					
				});
			}
			else
			{
				//set to next item
				if(x == list.length-1)
				{
					console.log("Done loading questions.");
					self._giveAnswerText(channelID, "Chat history loaded!");
					return;
				}
				x++;
				if(x<list.length)
				{
					loopArray(list);
				}
				
				
			}
		}
		
		//start loop
		loopArray(list);
	});
}
