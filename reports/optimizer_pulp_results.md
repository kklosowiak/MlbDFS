# 🏆 June 22 MLB DFS Optimizations (PuLP Solver)
Generated from **OMEGA results (v17.4)** and DraftKings salaries. Evaluated using raw **Individual Player Scores** for max projections, and **Blended Ratings** (incorporating confidence/slate context).

## ⚾ Premium Pitcher Board
| Pitcher | Team | Salary | OMEGA Alpha | Blended Rating | SIERA | Conf |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Dylan Cease | TOR | $10,000 | 135.8 | 113.9 | 2.68 | 92% |
| Hunter Brown | HOU | $10,800 | 114.8 | 100.4 | 2.20 | 86% |
| Brandon Woodruff | MIL | $8,700 | 106.0 | 98.0 | 3.66 | 90% |
| Gavin Williams | CLE | $9,300 | 84.8 | 73.9 | 3.84 | 63% |
| Kyle Bradish | BAL | $8,500 | 87.3 | 73.7 | 4.27 | 60% |
| Andre Pallante | STL | $8,000 | 68.0 | 71.5 | 3.87 | 75% |


## 🏟️ Premium Hitter Board (Top Value & Projections)
| Player | Team | Pos | Salary | Player Score | Blended Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| JJ Bleday | CIN | OF | $5,200 | 108.4 | 97.2 |
| Jake Bauers | MIL | 1B/OF | $4,900 | 107.8 | 96.9 |
| Yordan Alvarez | HOU | OF | $6,000 | 107.3 | 98.7 |
| Jackson Chourio | MIL | OF | $5,500 | 105.5 | 102.8 |
| Nathaniel Lowe | CIN | 1B | $3,500 | 94.8 | 89.4 |
| Royce Lewis | MIN | 1B | $3,600 | 90.1 | 95.0 |
| Juan Soto | NYM | OF | $5,800 | 88.3 | 76.2 |
| Alec Burleson | STL | 1B | $4,400 | 88.0 | 94.0 |
| Freddie Freeman | LAD | 1B | $5,200 | 87.7 | 87.8 |
| Sam Antonacci | CWS | OF | $3,800 | 84.6 | 88.3 |


## 📈 Optimal Lineups (Raw Player Projections)
These lineups maximize pure expected score on DraftKings.
### Pure Optimal Lineup (No Stacking Constraints)
**Total Score/Rating: 920.5 | Salary: $49,800**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Brandon Woodruff** | MIL | $8,700 | 106.0 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| C | **Sam Huff** | BAL | $2,300 | 58.4 |
| 1B | **Nathaniel Lowe** | CIN | $3,500 | 94.8 |
| 2B | **Will Wagner** | SD | $2,100 | 50.4 |
| 3B | **Coby Mayo** | BAL | $3,100 | 72.0 |
| SS | **Mookie Betts** | LAD | $4,500 | 81.4 |
| OF1 | **Jake Bauers** | MIL | $4,900 | 107.8 |
| OF2 | **JJ Bleday** | CIN | $5,200 | 108.4 |
| OF3 | **Jackson Chourio** | MIL | $5,500 | 105.5 |


### Brewers (5) + Cardinals (2) Stack
**Total Score/Rating: 840.5 | Salary: $49,900**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Sam Aldegheri** | LAA | $5,300 | 59.5 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| C | **Ivan Herrera** | STL | $4,300 | 62.0 |
| 1B | **Alec Burleson** | STL | $4,400 | 88.0 |
| 2B | **Brice Turang** | MIL | $5,700 | 77.3 |
| 3B | **Joey Ortiz** | MIL | $2,300 | 45.0 |
| SS | **Bo Bichette** | NYM | $4,200 | 75.7 |
| OF1 | **Garrett Mitchell** | MIL | $3,300 | 83.9 |
| OF2 | **Jackson Chourio** | MIL | $5,500 | 105.5 |
| OF3 | **Jake Bauers** | MIL | $4,900 | 107.8 |


### Brewers (4) + Cardinals (3) Stack
**Total Score/Rating: 849.3 | Salary: $50,000**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| SP2 | **Brandon Woodruff** | MIL | $8,700 | 106.0 |
| C | **Ivan Herrera** | STL | $4,300 | 62.0 |
| 1B | **Alec Burleson** | STL | $4,400 | 88.0 |
| 2B | **JJ Wetherholt** | STL | $4,500 | 64.9 |
| 3B | **Will Wagner** | SD | $2,100 | 50.4 |
| SS | **Joey Ortiz** | MIL | $2,300 | 45.0 |
| OF1 | **Jake Bauers** | MIL | $4,900 | 107.8 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 83.9 |
| OF3 | **Jackson Chourio** | MIL | $5,500 | 105.5 |


### Brewers (5) + Dodgers (3) Stack
**Total Score/Rating: 795.5 | Salary: $50,000**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| SP2 | **Sam Aldegheri** | LAA | $5,300 | 59.5 |
| C | **Dalton Rushing** | LAD | $4,100 | 52.6 |
| 1B | **Jake Bauers** | MIL | $4,900 | 107.8 |
| 2B | **Brice Turang** | MIL | $5,700 | 77.3 |
| 3B | **Tommy Edman** | LAD | $3,600 | 37.8 |
| SS | **Mookie Betts** | LAD | $4,500 | 81.4 |
| OF1 | **Jackson Chourio** | MIL | $5,500 | 105.5 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 83.9 |
| OF3 | **Sal Frelick** | MIL | $3,100 | 53.9 |


### Brewers (5) + Twins (3) Stack
**Total Score/Rating: 841.1 | Salary: $49,600**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| SP2 | **Kyle Bradish** | BAL | $8,500 | 87.3 |
| C | **Victor Caratini** | MIN | $3,100 | 49.9 |
| 1B | **Royce Lewis** | MIN | $3,600 | 90.1 |
| 2B | **Brice Turang** | MIL | $5,700 | 77.3 |
| 3B | **Joey Ortiz** | MIL | $2,300 | 45.0 |
| SS | **Ryan Kreidler** | MIN | $2,700 | 58.5 |
| OF1 | **Garrett Mitchell** | MIL | $3,300 | 83.9 |
| OF2 | **Jackson Chourio** | MIL | $5,500 | 105.5 |
| OF3 | **Jake Bauers** | MIL | $4,900 | 107.8 |


### Dodgers (5) + Brewers (3) Stack
**Total Score/Rating: 783.9 | Salary: $49,900**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Brandon Woodruff** | MIL | $8,700 | 106.0 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 135.8 |
| C | **Dalton Rushing** | LAD | $4,100 | 52.6 |
| 1B | **Freddie Freeman** | LAD | $5,200 | 87.7 |
| 2B | **Tommy Edman** | LAD | $3,600 | 37.8 |
| 3B | **Joey Ortiz** | MIL | $2,300 | 45.0 |
| SS | **Mookie Betts** | LAD | $4,500 | 81.4 |
| OF1 | **Jake Bauers** | MIL | $4,900 | 107.8 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 83.9 |
| OF3 | **Ryan Ward** | LAD | $3,300 | 45.9 |


## 🎯 Optimal Lineups (Blended Slate Context & Confidence)
These lineups incorporate OMEGA's confidence modifiers (weather, bullpen, steam, splits).
### Pure Optimal Blended Lineup
**Total Score/Rating: 904.6 | Salary: $50,000**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Brandon Woodruff** | MIL | $8,700 | 98.0 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 113.9 |
| C | **Sam Huff** | BAL | $2,300 | 73.2 |
| 1B | **Royce Lewis** | MIN | $3,600 | 95.0 |
| 2B | **JJ Wetherholt** | STL | $4,500 | 82.5 |
| 3B | **Bo Bichette** | NYM | $4,200 | 80.8 |
| SS | **Ryan Kreidler** | MIN | $2,700 | 69.2 |
| OF1 | **Jackson Chourio** | MIL | $5,500 | 102.8 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 92.0 |
| OF3 | **JJ Bleday** | CIN | $5,200 | 97.2 |


### Brewers (5) + Cardinals (2) Blended Stack
**Total Score/Rating: 861.4 | Salary: $49,900**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Sam Aldegheri** | LAA | $5,300 | 57.8 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 113.9 |
| C | **Ivan Herrera** | STL | $4,300 | 77.0 |
| 1B | **Alec Burleson** | STL | $4,400 | 94.0 |
| 2B | **Brice Turang** | MIL | $5,700 | 79.7 |
| 3B | **Bo Bichette** | NYM | $4,200 | 80.8 |
| SS | **Joey Ortiz** | MIL | $2,300 | 66.5 |
| OF1 | **Garrett Mitchell** | MIL | $3,300 | 92.0 |
| OF2 | **Jake Bauers** | MIL | $4,900 | 96.9 |
| OF3 | **Jackson Chourio** | MIL | $5,500 | 102.8 |


### Brewers (4) + Cardinals (3) Blended Stack
**Total Score/Rating: 877.6 | Salary: $49,700**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Brandon Woodruff** | MIL | $8,700 | 98.0 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 113.9 |
| C | **Ivan Herrera** | STL | $4,300 | 77.0 |
| 1B | **Alec Burleson** | STL | $4,400 | 94.0 |
| 2B | **JJ Wetherholt** | STL | $4,500 | 82.5 |
| 3B | **Joey Ortiz** | MIL | $2,300 | 66.5 |
| SS | **Bo Bichette** | NYM | $4,200 | 80.8 |
| OF1 | **Sal Frelick** | MIL | $3,100 | 76.0 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 92.0 |
| OF3 | **Jake Bauers** | MIL | $4,900 | 96.9 |


### Brewers (5) + Dodgers (3) Blended Stack
**Total Score/Rating: 811.5 | Salary: $49,000**

| Slot | Player | Team | Salary | Score/Rating |
| :--- | :--- | :--- | :--- | :--- |
| SP1 | **Sam Aldegheri** | LAA | $5,300 | 57.8 |
| SP2 | **Dylan Cease** | TOR | $10,000 | 113.9 |
| C | **Dalton Rushing** | LAD | $4,100 | 54.3 |
| 1B | **Freddie Freeman** | LAD | $5,200 | 87.8 |
| 2B | **Brice Turang** | MIL | $5,700 | 79.7 |
| 3B | **Joey Ortiz** | MIL | $2,300 | 66.5 |
| SS | **Mookie Betts** | LAD | $4,500 | 80.7 |
| OF1 | **Sal Frelick** | MIL | $3,100 | 76.0 |
| OF2 | **Garrett Mitchell** | MIL | $3,300 | 92.0 |
| OF3 | **Jackson Chourio** | MIL | $5,500 | 102.8 |

