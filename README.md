# nba_game_ratings

The purpose of this project is to answer the question: "What's the best NBA game on TV right now?"

I often asked myself this question during grad school when I would throw on some league pass in the background while completing work, and I put this together as a fun side project to learn web scraping.

I did a substantial update of the code in November 2022 (the host site's HTML had changed warranting some updates to the script).

For future work, I'm curious to create a truly real-time version that listens for updates from the original NBA scoreboard site (rather than requiring a user refresh), and also to make cosmetic enhancements to the game rating dashboard.

To run the code, simply clone the repo and from the command line run: "bokeh serve --show nba_game_ratings.py" and an interactive dashboard will appear in your browser.


Here's a quick overview of the various files:

<b>01) Train Model</b>

To start, I needed a way to rate games based on their watchability. The approach I decided on was to simulate various game scenarios and then manually rate them to create a labeled data set to model. I choose this route rather than developing a rule set, because I wanted the model to discover my subjective preferences rather than provide my assumptions up front.

I choose to simulate game scenarios with various time remaining, scoring margins, and quality of matchup. What I envisioned for matchup grades are:

A - Both teams are playoff teams
<br> B - One team is a playoff team, the other is a playoff contender
<br> C - Both teams are playoff contenders
<br> D - One team is a playoff contender the other is tanking
<br> E - Both teams are tanking

Here is what I had in mind with the ratings (the final output is put on a ten-point scale):

5 - You should probably stop second-screening and watch the game
<br> 4 - This is a good game worth watching
<br> 3 - Ok
<br> 2 - Not great
<br> 1 - This really isn't worth having on, go throw on some music instead

<b>02) Standings Data</b>

In order to grade the quality of the matchup, I scraped the current standings, and calculated a probability to make the playoffs, using a binomial distribution and assuming the current win percentage is reflective of future play.

<b>03) Scrape Scoreboard</b>

This is the code that's needed to scrape the latest data off of the NBA scoreboard.

<b>04) Rate Games</b>

New ratings predictions are made for the current games on the NBA scoreboard using the model trained in step 1

<b>05) Bokeh Script</b>

I put together a script using bokeh server to display current games, upcoming games, and finished games along with a timestamp for when the data was last pulled. There is a refresh button the user can press which will provide updated game scores/ratings.
