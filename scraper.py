import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver

years = list(range(2024, 2023, -1))
standings_url = "https://fbref.com/en/comps/9/Premier-League-Stats"

driver = webdriver.Chrome()

all_matches = []

for year in years:
    driver.get(standings_url)
    time.sleep(5)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    standings_table = soup.select('table.stats_table')[0]

    links = [l.get("href") for l in standings_table.find_all('a')]
    links = [l for l in links if '/squads/' in l]
    team_urls = [f"https://fbref.com{l}" for l in links]
    
    previous_season = soup.select("a.prev")[0].get("href")
    standings_url = f"https://fbref.com{previous_season}"
    
    for team_url in team_urls:
        team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
        driver.get(team_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        matches = pd.read_html(str(soup), match="Scores & Fixtures")[0]
        
        for stat_type in ["Shooting", "Goalkeeping", "Passing", "Passing Types", 
                          "Goal and Shot Creation", "Defensive Actions", "Possession", "Miscellaneous Stats"]:
            links = [l.get("href") for l in soup.find_all('a')]
            links = [l for l in links if l and f'all_comps/{stat_type}/' in l]
            if not links:
                continue
            driver.get(f"https://fbref.com{links[0]}")
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            stat_table = pd.read_html(str(soup), match=stat_type.capitalize())[0]
            stat_table.columns = stat_table.columns.droplevel()
            
            try:
                team_data = matches.merge(stat_table, on="Date")
            except ValueError:
                continue
            
            team_data = team_data[team_data["Comp"] == "Premier League"]
            team_data["Season"] = year
            team_data["Team"] = team_name
            all_matches.append(team_data)
            
            time.sleep(1)

driver.quit()
match_df = pd.concat(all_matches)
match_df.columns = [c.lower() for c in match_df.columns]
match_df.to_csv("matches.csv")