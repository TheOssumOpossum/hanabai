On 10,000 simulations

v0.1: Play Chop!
average_score: 1.2734 max_score: 11

v0.2: Save criticals... Play Chop!
average_score: 1.4358 max_score: 12

v0.3.0: Save criticals, if there is a player with a one-away clue then repetitively as long as it's a 'good touch', if there are no clues to give, play right-most clued card as long as it could be playable
simulations:10000 average_score:4.9033 max_score:18 strikeout_rate:0.9894 bottomout_rate:0.0106 victory_rate:0.0

v0.3.1: Same as 0.3.0 but prefer touching fewer cards.
simulations:10000 average_score:8.4601 max_score:19 strikeout_rate:0.8941 bottomout_rate:0.1059 victory_rate:0.0

v0.4.0: Updated GTP from 0.3, clues that touch 0 new cards are no good, prefer touching more cards. This does slightly better than before, note the higher max score.
simulations:10000 average_score:4.7354 max_score:22 strikeout_rate:0.9979 bottomout_rate:0.0021 victory_rate:0.0

v0.4.1: prefer touching fewer cards, this is an improvement over 0.3.0 but significantly far behind 0.3.1 counterpart. The aggressive discarding since clues were spammed lead to fewer bombs and a lower strikeout rate, but at least the max score is higher.
simulations:10000 average_score:5.9533 max_score:21 strikeout_rate:0.9889 bottomout_rate:0.0111 victory_rate:0.0

v0.5.0: Added a check for 'clues-left-to-right', prefer touching more cards. Significant improvment to previous version, highest max score!
simulations:10000 average_score:8.6814 max_score:22 strikeout_rate:0.9674 bottomout_rate:0.0326 victory_rate:0.0

v0.5.1: prefer touching fewer cards. Best version yet! This still outperforms the the high touch version since players play left-to-right regardless of their most recent clue.
simulations:10000 average_score:9.5844 max_score:21 strikeout_rate:0.928 bottomout_rate:0.072 victory_rate:0.0

v0.6.0: Added notion of 'play' clues, now the player will try to identify the focus of the card and will only play the focus unless they are sure the card is playable, prefer touching more cards. I'm not super confident this is bug-free but it seems that playing more aggressively will result in a higher score.
simulations:10000 average_score:5.4113 max_score:20 strikeout_rate:0.99 bottomout_rate:0.01 victory_rate:0.0

v0.6.1: prefer touching fewer cards. score has gone down a little bit but strikeout rate is down significantly, obviously the players are much more patient but seem to not be playing cards when needed
simulations:10000 average_score:9.5024 max_score:21 strikeout_rate:0.8185 bottomout_rate:0.1815 victory_rate:0.0

v0.7.0: Updated GTP, don't clue cards that have already been clued in other hands, prefer touching more cards. It seems like there is some sort of bug, I saw a player cluing Red after the player had received a 1 clue. However, it worked out because the player proceeded to play both the red 1 (initially marked as 1) and the red 2 (subsequently marked as 2 before the r1 played). Doesn't seem to have significant improvment.

v0.7.1: prefer touching fewer cards. Strikeout rate decreased dramatically with an increase in average score. Best version yet!
simulations:10000 average_score:9.7478 max_score:21 strikeout_rate:0.809 bottomout_rate:0.191 victory_rate:0.0