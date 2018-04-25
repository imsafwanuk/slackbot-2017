CREATE TABLE slackfaqtestTable(
  id INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  question varchar(10000),
  ts varchar(50),
  PRIMARY KEY (id)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

INSERT INTO FAQTable (id, question, ts) VALUES
(1, 'where i can find it', 'p1490918243341475'),
(2, 'How come?', 'p1489716197230985'),
(3, 'How old', 'p1489574664075600');







CREATE TABLE teamTokens(
  teamID varchar(200),
  teamName varchar(200),
  userToken varchar(500),
  botToken varchar(500),
  botID varchar(100),
  PRIMARY KEY (teamID)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;




CREATE TABLE events(
  ts varchar(200),
  channelID varchar(200),
  text varchar(10000),
  PRIMARY KEY (ts,channelID)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;


select text from events where (ts = "1496152535.134733") and (channelID = "C5JM0L2M6");



CREATE TABLE teamChannels(
  channelID varchar(200),
  teamID varchar(200),
  PRIMARY KEY (channelID)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;



CREATE TABLE teamGroups(
  groupID varchar(200),
  teamID varchar(200),
  PRIMARY KEY (groupID)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

