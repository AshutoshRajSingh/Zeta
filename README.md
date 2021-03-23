# Zeta

Another general purpose discord bot with most of the usual quirks including a moderation system, an on message level/exp 
system, reaction roles and the like.
## Setting up:
The basic requirements are listed as follows:
 - Python 3.8.x with pip
 - A Postgresql 12 database with a user with superuser permissions

If you've got them down, the rest is pretty straightforward, first navigate to the outermost dir in the repository, open
a terminal and type in:
```shell
pip install -r requirements.txt
```
The next thing you'll need is a postgresql database to be used by the bot. Skip if you've already created one. 

Now you'll need to create two environment variables in your operating system, the method varies in between OSes so 
you'll have to look into your specific os for it.
```
DATABASE_URL:  the url to the postgresql database
BOT_TOKEN: The api token for your bot account
```
The url for your database is usually given in the format:
```
postgres://<username>:<password>@<host>:<port>/<database_name>
```
After that is done, the next thing is to set up the database in the format the bot uses it, ie creating the tables etc.
To do that, open your terminal in the project base dir, and type in:
```shell
python launcher.py db init
```
If the last line says "Db initialized successfully", you're good to go.

## Running
To run the bot, open your terminal in the base dir, and type in:
```shell
python launcher.py bot start
```

## Usage
The default prefix for every server is `.`, use `.help` in your server to get more information.  
Note that things like the on message level/exp system are disabled by default, use the `plugin` and `help plugin` 
commands for more info.

