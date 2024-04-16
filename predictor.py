import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score

class MissingDict(dict):
    __missing__ = lambda self, key: key

def rolling_averages(group, cols, new_cols):
    group = group.sort_values("date")
    rolling_stats = group[cols].rolling(3, closed='left').mean()
    group[new_cols] = rolling_stats
    group = group.dropna(subset=new_cols)
    return group

def make_predictions(data, predictors):
    train = data[data["date"] < '2022-01-01']
    test = data[data["date"] > '2022-01-01']
    rf.fit(train[predictors], train["target"])
    preds = rf.predict(test[predictors])
    combined = pd.DataFrame(dict(actual=test["target"], predicted=preds), index=test.index)
    error = precision_score(test["target"], preds)
    return combined, error

# cleaning the data for the ML model
matches = pd.read_csv("matches.csv", index_col=0)
matches["date"] = pd.to_datetime(matches["date"])
matches["target"] = (matches["result"] == "W").astype("int")
matches["venue_code"] = matches["venue"].astype("category").cat.codes
matches["opp_code"] = matches["opponent"].astype("category").cat.codes
matches["hour"] = matches["time"].str.replace(":.+", "", regex=True).astype("int")
matches["day_code"] = matches["date"].dt.dayofweek

# creating predictors for the initial ML model
rf = RandomForestClassifier(n_estimators=50, min_samples_split=10, random_state=1)
train = matches[matches["date"] < '2022-01-01']
test = matches[matches["date"] > '2022-01-01']
predictors = ["venue_code", "opp_code", "hour", "day_code"]
rf.fit(train[predictors], train["target"])
preds = rf.predict(test[predictors])

# returns a precision score for our model (sample data file is ~47% -> ~61%)
precision_score(test["target"], preds)

# improving precision with rolling averages
grouped_matches = matches.groupby("team")
group = grouped_matches.get_group("Manchester City").sort_values("date")
cols = ["gf", "ga", "sh", "sot", "dist", "fk", "pk", "pkatt"]
new_cols = [f"{c}_rolling" for c in cols]
matches_rolling = matches.groupby("team").apply(lambda x: rolling_averages(x, cols, new_cols))
matches_rolling = matches_rolling.droplevel('team')
matches_rolling.index = range(matches_rolling.shape[0])

# retraining our ML model
combined, error = make_predictions(matches_rolling, predictors + new_cols)
combined = combined.merge(matches_rolling[["date", "team", "opponent", "result"]], left_index=True, right_index=True)

# combining home and away predictions
map_values = {"Brighton and Hove Albion": "Brighton", "Manchester United": "Manchester Utd", "Newcastle United": "Newcastle Utd", "Tottenham Hotspur": "Tottenham", "West Ham United": "West Ham", "Wolverhampton Wanderers": "Wolves"} 
mapping = MissingDict(**map_values)
combined["new_team"] = combined["team"].map(mapping)
merged = combined.merge(combined, left_on=["date", "new_team"], right_on=["date", "opponent"])
merged[(merged["predicted_x"] == 1) & (merged["predicted_y"] ==0)]["actual_x"].value_counts()

def predict_winner(team1, team2):
    # Get the last match for each team
    team1_data = matches_rolling[matches_rolling['team'] == team1].iloc[-1]
    team2_data = matches_rolling[matches_rolling['team'] == team2].iloc[-1]

    # Prepare the data for prediction
    team1_data = team1_data[predictors + new_cols].values.reshape(1, -1)
    team2_data = team2_data[predictors + new_cols].values.reshape(1, -1)

    # Make predictions
    team1_pred = rf.predict(team1_data)
    team2_pred = rf.predict(team2_data)

    # Return the predicted winner
    if team1_pred > team2_pred:
        return team1
    elif team1_pred < team2_pred:
        return team2
    else:
        return 'Draw'

#  should output 'Liverpool'
# print(predict_winner('Manchester United', 'Liverpool'))