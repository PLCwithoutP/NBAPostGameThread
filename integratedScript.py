import praw
from nba_api.live.nba.endpoints import boxscore
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder

# 🏀 Initialize Reddit API (using praw.ini for credentials)
reddit = praw.Reddit("bot")
#subreddit = reddit.subreddit("NBAPostGameDiscussion")
subreddit = reddit.subreddit("rockets")

# 🏀 Get Houston Rockets' Team ID
nba_teams = teams.get_teams()
rockets = next(team for team in nba_teams if team["abbreviation"] == "HOU")
rockets_id = rockets["id"]

# 🏀 Get Most Recent Game ID
gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=rockets_id)
recent_games = gamefinder.get_data_frames()[0]
current_game_id = recent_games.iloc[0]["GAME_ID"]

# 🏀 Fetch Box Score Data
box = boxscore.BoxScore(current_game_id)
game_data = box.get_dict()

# 🏀 Extract Game Info
home_team = game_data["game"]["homeTeam"]
away_team = game_data["game"]["awayTeam"]
home_score = home_team["score"]
away_score = away_team["score"]
game_date = game_data["game"]["gameTimeUTC"]
stadium = game_data["game"]["arena"]["arenaName"]
city = game_data["game"]["arena"]["arenaCity"]
referees = ", ".join([ref["name"] for ref in game_data["game"]["officials"]])

# 🏀 Determine Winner and Format Title
if home_score > away_score:
    winning_team, losing_team, final_score = home_team["teamName"], away_team["teamName"], f"{home_score}-{away_score}"
else:
    winning_team, losing_team, final_score = away_team["teamName"], home_team["teamName"], f"{away_score}-{home_score}"

title = f"[Post-game Thread]{winning_team} defeats {losing_team} by {final_score}"

# 🏀 Check if Post Already Exists
def post_exists(title):
    for submission in subreddit.new(limit=10):  # Check last 10 posts
        if submission.title == title and submission.author == reddit.user.me():
            return True
    return False

# 🏀 Extract Player Stats & Compute Team Totals
def format_players(players):
    """Formats player stats into a properly structured Markdown table for Reddit, including team totals."""
    headers = "| Player | MIN | PTS | OREB | DREB | TREB | AST | STL | BLK | TO | +/- | FGM | FGA | 3PM | 3PA | FTM | FTA |"
    separator = "|:------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"

    table = [headers, separator]
    team_totals = {key: 0 for key in ["minutes", "points", "reboundsOffensive", "reboundsDefensive", "reboundsTotal", "assists", 
                                       "steals", "blocks", "turnovers", "plusMinusPoints", "fieldGoalsMade", 
                                       "fieldGoalsAttempted", "threePointersMade", "threePointersAttempted", 
                                       "freeThrowsMade", "freeThrowsAttempted"]}

    for player in players:
        stats = player["statistics"]
        formattedMinutes = minutesFormatter(stats['minutes'])
        row = f"| {player['name']} | {formattedMinutes} | {stats['points']} | {stats['reboundsOffensive']} | {stats['reboundsDefensive']} | {stats['reboundsTotal']} | {stats['assists']} | {stats['steals']} | {stats['blocks']} | {stats['turnovers']} | {stats['plusMinusPoints']} | {stats['fieldGoalsMade']} | {stats['fieldGoalsAttempted']} | {stats['threePointersMade']} | {stats['threePointersAttempted']} | {stats['freeThrowsMade']} | {stats['freeThrowsAttempted']} |"
        table.append(row)

        for key in team_totals:
            if not key == 'minutes':
                team_totals[key] += stats[key]

    # Add team totals row
    totals_row = f"| **Team Totals** | - | {team_totals['points']} | {team_totals['reboundsOffensive']} | {team_totals['reboundsDefensive']} | {team_totals['reboundsTotal']} | {team_totals['assists']} | {team_totals['steals']} | {team_totals['blocks']} | {team_totals['turnovers']} | - | {team_totals['fieldGoalsMade']} | {team_totals['fieldGoalsAttempted']} | {team_totals['threePointersMade']} | {team_totals['threePointersAttempted']} | {team_totals['freeThrowsMade']} | {team_totals['freeThrowsAttempted']} |"
    table.append(totals_row)

    return "\n".join(table)

def minutesFormatter(minuteStringData):
    finalFormattedData = minuteStringData.split('M')[0].split('T')[1] + ':' + minuteStringData.split('M')[1].split('.')[0]
    return finalFormattedData

home_table = format_players(home_team["players"])
away_table = format_players(away_team["players"])

# 🏀 Create Quarter-by-Quarter Score Table
quarter_scores = ["| Quarter | 1st | 2nd | 3rd | 4th |"]
quarter_scores.append("|:-------|:---:|:---:|:---:|:---:|")
home_quarters = home_team["periods"]
away_quarters = away_team["periods"]

home_row = f"| {home_team['teamTricode']} | " + " | ".join(str(q["score"]) for q in home_quarters) + " |"
away_row = f"| {away_team['teamTricode']} | " + " | ".join(str(q["score"]) for q in away_quarters) + " |"

quarter_scores.extend([home_row, away_row])
quarter_table = "\n".join(quarter_scores)

# 🏀 Create Post Body
body = f"""
**🏀 Final Score:**  
**{away_team['teamTricode']} {away_score} - {home_team['teamTricode']} {home_score}**  

---

### 📅 Game Details
- **Date:** {game_date}  
- **Stadium:** {stadium}, {city}  
- **Referees:** {referees}  

---

### 📊 Quarter-by-Quarter Scores
{quarter_table}

---

### {away_team['teamTricode']} Player Stats  
{away_table}

---

### {home_team['teamTricode']} Player Stats  
{home_table}
"""

# 🏀 Post to Reddit
def post_game_thread(title, body):
    """Posts the formatted game data to the subreddit if it hasn't been posted already."""
    if post_exists(title):
        print(f"⚠️ Post already exists: {title}")
        return

    try:
        post = subreddit.submit(title, selftext=body)
        print(f"✅ Post created: {post.url}")
    except Exception as e:
        print(f"❌ Error posting to Reddit: {e}")

# Run the bot
post_game_thread(title, body)
